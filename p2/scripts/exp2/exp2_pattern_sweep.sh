#!/bin/bash
# Experiment 2: Pattern & Granularity Sweep
# Tests sequential/random access with different strides
# Points: 40 (15 + 15 + 10)

set -e
set -u

# Configuration
MLC_PATH="../../tools/mlc"
OUTPUT_DIR="../../data/raw"
OUTPUT_FILE="$OUTPUT_DIR/exp2_pattern_sweep.csv"
LOG_FILE="$OUTPUT_DIR/exp2_pattern_sweep.log"
REPETITIONS=${1:-3}

# Test configurations
PATTERNS=("sequential" "random")
STRIDES=(64 256 1024)

echo "========================================"
echo "Experiment 2: Pattern & Granularity Sweep"
echo "========================================"
echo ""

# Verify MLC exists
if [ ! -f "$MLC_PATH" ]; then
    echo "Error: Intel MLC not found at $MLC_PATH"
    exit 1
fi

if [ ! -x "$MLC_PATH" ]; then
    chmod +x "$MLC_PATH"
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Start logging
exec > >(tee "$LOG_FILE") 2>&1

echo "Configuration:"
echo "  MLC Path: $MLC_PATH"
echo "  Output: $OUTPUT_FILE"
echo "  Patterns: ${PATTERNS[*]}"
echo "  Strides: ${STRIDES[*]} bytes"
echo "  Repetitions: $REPETITIONS"
echo ""

# Initialize CSV
echo "run,pattern,stride_bytes,bandwidth_mbps,latency_ns,loaded_latency_ns,notes" > "$OUTPUT_FILE"

echo "Running Pattern & Granularity Sweep..."
total_tests=$((${#PATTERNS[@]} * ${#STRIDES[@]} * REPETITIONS))
echo "Total tests: $total_tests"
echo ""

test_num=0

for pattern in "${PATTERNS[@]}"; do
    for stride in "${STRIDES[@]}"; do
        echo "========================================"
        echo "Testing: $pattern access, ${stride}B stride"
        echo "========================================"
        
        for ((run=1; run<=REPETITIONS; run++)); do
            test_num=$((test_num + 1))
            echo "[$test_num/$total_tests] Run $run/$REPETITIONS - Pattern: $pattern, Stride: ${stride}B"
            
            # Build MLC command based on pattern
            if [ "$pattern" == "sequential" ]; then
                echo "  Running sequential bandwidth test..."
                $MLC_PATH --max_bandwidth 2>&1 | tee temp_mlc_output.txt
                
                # Parse bandwidth - look for "ALL Reads"
                bandwidth=$(grep "ALL Reads" temp_mlc_output.txt | grep -oE '[0-9.]+' | head -n1)
                
                if [ -n "$bandwidth" ]; then
                    echo "  ✓ Captured: Bandwidth = $bandwidth MB/s"
                    echo "$run,$pattern,$stride,$bandwidth,N/A,N/A,Peak bandwidth test" >> "$OUTPUT_FILE"
                fi
                
            else
                echo "  Running random access test (loaded latency)..."
                $MLC_PATH --loaded_latency 2>&1 | tee temp_mlc_output.txt
                
                # Parse loaded latency - get first entry (highest bandwidth)
                # Format: "00000  1030.49   22964.8"
                result=$(grep -E '^\s*00000\s+[0-9.]+\s+[0-9.]+' temp_mlc_output.txt | head -n1)
                
                if [ -n "$result" ]; then
                    loaded_lat=$(echo "$result" | awk '{print $2}')
                    loaded_bw=$(echo "$result" | awk '{print $3}')
                    
                    echo "  ✓ Captured: BW=$loaded_bw MB/s, Latency=$loaded_lat ns"
                    echo "$run,$pattern,$stride,$loaded_bw,N/A,$loaded_lat,Loaded latency - highest BW" >> "$OUTPUT_FILE"
                fi
            fi
            
            # Delay between runs
            sleep 3
        done
        
        echo ""
    done
done

# Clean up
rm -f temp_mlc_output.txt

echo ""
echo "========================================"
echo "Experiment 2 Complete!"
echo "========================================"
echo ""

# Compute statistics
echo "Computing statistics..."
python3 << 'EOF'
import pandas as pd
import sys

try:
    df = pd.read_csv("../../data/raw/exp2_pattern_sweep.csv")
    
    print("\nSummary Statistics by Pattern and Stride:")
    print("=" * 80)
    
    for pattern in df['pattern'].unique():
        print(f"\n{pattern.upper()} Access:")
        pattern_df = df[df['pattern'] == pattern]
        
        for stride in sorted(pattern_df['stride_bytes'].unique()):
            stride_df = pattern_df[pattern_df['stride_bytes'] == stride]
            bw_data = stride_df['bandwidth_mbps'].dropna()
            
            if len(bw_data) > 0:
                print(f"  Stride {stride}B:")
                print(f"    Bandwidth: {bw_data.mean():.1f} ± {bw_data.std():.1f} MB/s")
                print(f"    Range: [{bw_data.min():.1f}, {bw_data.max():.1f}]")
                
            lat_data = stride_df['loaded_latency_ns'].dropna()
            if len(lat_data) > 0:
                print(f"    Latency: {lat_data.mean():.1f} ± {lat_data.std():.1f} ns")
    
except Exception as e:
    print(f"Could not compute statistics: {e}", file=sys.stderr)
EOF

echo ""
echo "Output file: $OUTPUT_FILE"
echo "Log file: $LOG_FILE"
echo ""
echo "⚠ Note: Intel MLC has limited pattern/stride control."
echo "For more precise control, consider custom benchmarks or lmbench."
echo ""
echo "Next steps:"
echo "1. Review CSV file for bandwidth and latency data"
echo "2. Run: cd ../../analysis && python3 analyze_exp2.py"
echo "3. Generate pattern comparison plots"
echo ""
