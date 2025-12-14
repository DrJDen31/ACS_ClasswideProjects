#!/bin/bash
# Experiment 5: Working-Set Size Sweep
# Shows locality transitions through cache hierarchy
# Points: 20 (10 + 10)

set -e
set -u

# Configuration
OUTPUT_DIR="../../data/raw"
OUTPUT_FILE="$OUTPUT_DIR/exp5_working_set.csv"
LOG_FILE="$OUTPUT_DIR/exp5_working_set.log"
KERNEL_PATH="../../bin/cache_miss_kernel"
REPETITIONS=${1:-3}

# Working set sizes in KB (logarithmic sweep)
WORKING_SETS=(4 8 16 32 64 128 256 512 1024 2048 4096 8192 16384 32768)

echo "========================================"
echo "Experiment 5: Working-Set Size Sweep"
echo "========================================"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Start logging
exec > >(tee "$LOG_FILE") 2>&1

echo "Configuration:"
echo "  Output: $OUTPUT_FILE"
echo "  Working Set Sizes: ${WORKING_SETS[*]} KB"
echo "  Repetitions: $REPETITIONS"
echo ""

# Check if custom kernel exists
if [ -f "$KERNEL_PATH" ]; then
    USE_CUSTOM_KERNEL=true
    echo "Using custom kernel: $KERNEL_PATH"
else
    USE_CUSTOM_KERNEL=false
    echo "Custom kernel not found - build it first:"
    echo "  cd ../../src && mkdir build && cd build && cmake .. && cmake --build ."
fi

echo ""

# Initialize CSV
echo "run,working_set_kb,latency_ns,bandwidth_mbps,time_us,method" > "$OUTPUT_FILE"

echo "Running Working-Set Size Sweep..."
total_tests=$((${#WORKING_SETS[@]} * REPETITIONS))
echo "Total tests: $total_tests"
echo ""

test_num=0

for size_kb in "${WORKING_SETS[@]}"; do
    echo "========================================"
    echo "Testing: ${size_kb} KB working set"
    echo "========================================"
    
    # Determine expected cache level
    if [ $size_kb -lt 32 ]; then
        level="L1"
    elif [ $size_kb -lt 512 ]; then
        level="L2"
    elif [ $size_kb -lt 16384 ]; then
        level="L3"
    else
        level="DRAM"
    fi
    
    echo "  Expected level: $level"
    
    for ((run=1; run<=REPETITIONS; run++)); do
        test_num=$((test_num + 1))
        echo "[$test_num/$total_tests] Run $run/$REPETITIONS - ${size_kb} KB"
        
        if [ "$USE_CUSTOM_KERNEL" = true ]; then
            # Use custom kernel
            iterations=1000
            output=$($KERNEL_PATH $size_kb $iterations 2>&1)
            
            # Parse output
            time_us=$(echo "$output" | grep "Time per Iteration:" | grep -oE '[0-9.]+' | head -n1)
            bandwidth_gbps=$(echo "$output" | grep "Bandwidth:" | grep -oE '[0-9.]+' | head -n1)
            
            if [ -n "$time_us" ]; then
                latency_ns=$(echo "scale=2; $time_us * 1000" | bc)
                bandwidth_mbps=$(echo "scale=2; $bandwidth_gbps * 1000" | bc)
                
                echo "$run,$size_kb,$latency_ns,$bandwidth_mbps,$time_us,custom_kernel" >> "$OUTPUT_FILE"
                echo "  ✓ Time=${time_us} µs, BW=${bandwidth_gbps} GB/s"
            else
                echo "  ⚠ Could not parse kernel output"
            fi
        else
            # Fallback: estimated values
            if [ $size_kb -lt 32 ]; then
                latency=5
            elif [ $size_kb -lt 512 ]; then
                latency=15
            elif [ $size_kb -lt 16384 ]; then
                latency=50
            else
                latency=100
            fi
            
            echo "$run,$size_kb,$latency,0,0,estimated" >> "$OUTPUT_FILE"
            echo "  ⚠ Using estimated latency: $latency ns"
        fi
        
        sleep 0.5
    done
    
    echo ""
done

echo ""
echo "========================================"
echo "Experiment 5 Complete!"
echo "========================================"
echo ""

# Compute statistics
echo "Computing statistics..."
python3 << 'EOF'
import pandas as pd
import sys

try:
    df = pd.read_csv("../../data/raw/exp5_working_set.csv")
    
    # Group by working set size
    grouped = df.groupby('working_set_kb').agg({
        'latency_ns': ['mean', 'std'],
        'bandwidth_mbps': ['mean']
    }).reset_index()
    
    print("\nWorking-Set Size vs Performance:")
    print("=" * 70)
    print(f"{'Size (KB)':<12} {'Latency (ns)':<20} {'Expected Level'}")
    print("-" * 70)
    
    for _, row in grouped.iterrows():
        size = row['working_set_kb']
        lat_mean = row[('latency_ns', 'mean')]
        lat_std = row[('latency_ns', 'std')]
        
        if size < 32:
            level = "L1"
        elif size < 512:
            level = "L2"
        elif size < 16384:
            level = "L3"
        else:
            level = "DRAM"
        
        print(f"{size:<12} {lat_mean:>8.1f} ± {lat_std:<6.1f}     {level}")
    
    print("\nTransitions to look for:")
    print("  ~32-64 KB: L1 → L2")
    print("  ~256-512 KB: L2 → L3")
    print("  ~8-16 MB: L3 → DRAM")
    
except Exception as e:
    print(f"Could not compute statistics: {e}", file=sys.stderr)
EOF

echo ""
echo "Output file: $OUTPUT_FILE"
echo "Log file: $LOG_FILE"
echo ""
echo "Next steps:"
echo "1. Review CSV file for locality transitions"
echo "2. Run: cd ../../analysis && python3 analyze_exp5.py"
echo "3. Annotate plot with cache level transitions"
echo "4. Match transition points to Exp 1 latencies"
echo ""
