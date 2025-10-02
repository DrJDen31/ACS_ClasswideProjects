#!/bin/bash
# Experiment 3: Read/Write Mix Sweep
# Tests DRAM bandwidth under different R/W ratios
# Points: 30 (10 + 10 + 10)

set -e
set -u

# Configuration
MLC_PATH="../../tools/mlc"
OUTPUT_DIR="../../data/raw"
OUTPUT_FILE="$OUTPUT_DIR/exp3_rw_mix.csv"
LOG_FILE="$OUTPUT_DIR/exp3_rw_mix.log"
REPETITIONS=${1:-5}

echo "========================================"
echo "Experiment 3: Read/Write Mix Sweep"
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
echo "  Repetitions: $REPETITIONS"
echo "  Ratios: 100%R, 100%W, 70/30, 50/50"
echo ""

# Initialize CSV
echo "run,ratio,read_pct,write_pct,bandwidth_mbps,notes" > "$OUTPUT_FILE"

echo "Running Read/Write Mix Sweep..."
total_tests=$((4 * REPETITIONS))
echo "Total tests: $total_tests"
echo ""

test_num=0

# Test 100% Read
echo "========================================"
echo "Testing: 100% Read"
echo "========================================"

for ((run=1; run<=REPETITIONS; run++)); do
    test_num=$((test_num + 1))
    echo "[$test_num/$total_tests] Run $run/$REPETITIONS - 100% Read"
    
    $MLC_PATH --max_bandwidth 2>&1 | tee temp_mlc_output.txt
    
    # Parse "ALL Reads" line
    bandwidth=$(grep "ALL Reads" temp_mlc_output.txt | grep -oE '[0-9.]+' | head -n1)
    
    if [ -n "$bandwidth" ]; then
        echo "  ✓ Captured: $bandwidth MB/s"
        echo "$run,100% Read,100,0,$bandwidth,Peak read bandwidth" >> "$OUTPUT_FILE"
    fi
    
    sleep 2
done

echo ""

# Test 100% Write
echo "========================================"
echo "Testing: 100% Write"
echo "========================================"

for ((run=1; run<=REPETITIONS; run++)); do
    test_num=$((test_num + 1))
    echo "[$test_num/$total_tests] Run $run/$REPETITIONS - 100% Write"
    
    $MLC_PATH --max_bandwidth -W1 2>&1 | tee temp_mlc_output.txt
    
    # Parse bandwidth - look for write-specific line or general bandwidth
    bandwidth=$(grep -E "ALL.*Write|Stream-triad" temp_mlc_output.txt | grep -oE '[0-9.]+' | head -n1)
    
    if [ -n "$bandwidth" ]; then
        echo "  ✓ Captured: $bandwidth MB/s"
        echo "$run,100% Write,0,100,$bandwidth,Peak write bandwidth" >> "$OUTPUT_FILE"
    fi
    
    sleep 2
done

echo ""

# Test 70/30 R/W (3:1 ratio)
echo "========================================"
echo "Testing: 70/30 R/W"
echo "========================================"

for ((run=1; run<=REPETITIONS; run++)); do
    test_num=$((test_num + 1))
    echo "[$test_num/$total_tests] Run $run/$REPETITIONS - 70/30 R/W"
    
    $MLC_PATH --max_bandwidth -W3 2>&1 | tee temp_mlc_output.txt
    
    # Parse "3:1 Reads-Writes" line
    bandwidth=$(grep "3:1 Reads-Writes" temp_mlc_output.txt | grep -oE '[0-9.]+' | head -n1)
    
    if [ -n "$bandwidth" ]; then
        echo "  ✓ Captured: $bandwidth MB/s"
        echo "$run,70/30 R/W,70,30,$bandwidth,3:1 read/write mix" >> "$OUTPUT_FILE"
    fi
    
    sleep 2
done

echo ""

# Test 50/50 R/W (1:1 ratio)
echo "========================================"
echo "Testing: 50/50 R/W"
echo "========================================"

for ((run=1; run<=REPETITIONS; run++)); do
    test_num=$((test_num + 1))
    echo "[$test_num/$total_tests] Run $run/$REPETITIONS - 50/50 R/W"
    
    $MLC_PATH --max_bandwidth -W4 2>&1 | tee temp_mlc_output.txt
    
    # Parse "1:1 Reads-Writes" line
    bandwidth=$(grep "1:1 Reads-Writes" temp_mlc_output.txt | grep -oE '[0-9.]+' | head -n1)
    
    if [ -n "$bandwidth" ]; then
        echo "  ✓ Captured: $bandwidth MB/s"
        echo "$run,50/50 R/W,50,50,$bandwidth,1:1 read/write mix" >> "$OUTPUT_FILE"
    fi
    
    sleep 2
done

# Clean up
rm -f temp_mlc_output.txt

echo ""
echo "========================================"
echo "Experiment 3 Complete!"
echo "========================================"
echo ""

# Compute statistics
echo "Computing statistics..."
python3 << 'EOF'
import pandas as pd
import sys

try:
    df = pd.read_csv("../../data/raw/exp3_rw_mix.csv")
    
    print("\nSummary Statistics by R/W Ratio:")
    print("=" * 70)
    
    for ratio in df['ratio'].unique():
        data = df[df['ratio'] == ratio]['bandwidth_mbps']
        print(f"\n{ratio}:")
        print(f"  Mean:   {data.mean():.1f} MB/s")
        print(f"  Std:    {data.std():.1f} MB/s")
        print(f"  Range:  [{data.min():.1f}, {data.max():.1f}]")
        print(f"  CV:     {(data.std()/data.mean()*100):.2f}%")
    
except Exception as e:
    print(f"Could not compute statistics: {e}", file=sys.stderr)
EOF

echo ""
echo "Output file: $OUTPUT_FILE"
echo "Log file: $LOG_FILE"
echo ""
echo "Next steps:"
echo "1. Review CSV file for bandwidth data"
echo "2. Run: cd ../../analysis && python3 analyze_exp3.py"
echo "3. Compare R/W mix performance"
echo ""
echo "Expected observations:"
echo "  - Read bandwidth typically highest"
echo "  - Write bandwidth affected by buffer/cache effects"
echo "  - Mixed ratios show intermediate performance"
echo ""
