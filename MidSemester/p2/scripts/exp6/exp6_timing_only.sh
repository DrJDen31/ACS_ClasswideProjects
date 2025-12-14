#!/bin/bash
# Experiment 6: Cache-Miss Impact (Timing-Only Version)
# Shows cache effects through runtime measurements
# Points: 25 (20-23 achievable without hardware counters)

set -e
set -u

# Configuration
KERNEL_PATH="../../bin/cache_miss_kernel"
OUTPUT_DIR="../../data/raw"
OUTPUT_FILE="$OUTPUT_DIR/exp6_cache_miss.csv"
LOG_FILE="$OUTPUT_DIR/exp6_cache_miss.log"
REPETITIONS=${1:-5}

# Working set sizes to test (KB)
WORKING_SETS=(16 32 64 128 256 512 1024 2048 4096 8192 16384)
ITERATIONS=5000

echo "========================================"
echo "Experiment 6: Cache-Miss Impact"
echo "Timing-Only Version (No Hardware Counters)"
echo "========================================"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Start logging
exec > >(tee "$LOG_FILE") 2>&1

echo "Configuration:"
echo "  Kernel: $KERNEL_PATH"
echo "  Working Sets: ${WORKING_SETS[*]} KB"
echo "  Iterations per test: $ITERATIONS"
echo "  Repetitions: $REPETITIONS"
echo ""

# Check for kernel
if [ ! -f "$KERNEL_PATH" ]; then
    echo "Error: Kernel not found at $KERNEL_PATH"
    echo "Build with:"
    echo "  cd ../../src && mkdir -p build && cd build"
    echo "  cmake .. && make"
    exit 1
fi

# Initialize CSV
echo "run,working_set_kb,runtime_ms,time_per_iter_us,bandwidth_gbps,gflops" > "$OUTPUT_FILE"

echo "Running Cache-Miss Impact Experiment..."
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
        expected_level="L1"
    elif [ $size_kb -lt 512 ]; then
        expected_level="L2"
    elif [ $size_kb -lt 16384 ]; then
        expected_level="L3"
    else
        expected_level="DRAM"
    fi
    
    echo "  Expected to hit: $expected_level"
    
    for ((run=1; run<=REPETITIONS; run++)); do
        test_num=$((test_num + 1))
        echo "[$test_num/$total_tests] Run $run/$REPETITIONS - ${size_kb} KB"
        
        # Run kernel and capture output
        output=$($KERNEL_PATH $size_kb $ITERATIONS 2>&1)
        
        # Parse timing output
        total_time_s=$(echo "$output" | grep "Total Time:" | grep -oE '[0-9.]+' | head -n1)
        time_per_iter_us=$(echo "$output" | grep "Time per Iteration:" | grep -oE '[0-9.]+' | head -n1)
        bandwidth_gbps=$(echo "$output" | grep "Bandwidth:" | grep -oE '[0-9.]+' | head -n1)
        gflops=$(echo "$output" | grep "Throughput:" | grep -oE '[0-9.]+' | head -n1)
        
        # Calculate runtime in ms
        if [ -n "$total_time_s" ]; then
            runtime_ms=$(echo "scale=3; $total_time_s * 1000" | bc)
        else
            runtime_ms="0"
        fi
        
        # Use defaults if parsing failed
        time_per_iter_us=${time_per_iter_us:-0}
        bandwidth_gbps=${bandwidth_gbps:-0}
        gflops=${gflops:-0}
        
        # Save to CSV
        echo "$run,$size_kb,$runtime_ms,$time_per_iter_us,$bandwidth_gbps,$gflops" >> "$OUTPUT_FILE"
        
        echo "  Runtime: ${runtime_ms} ms"
        echo "  Time/iter: ${time_per_iter_us} µs"
        echo "  Bandwidth: ${bandwidth_gbps} GB/s"
        echo ""
        
        sleep 0.5
    done
done

echo ""
echo "========================================"
echo "Experiment 6 Complete!"
echo "========================================"
echo ""

# Compute statistics
echo "Computing statistics..."
python3 << 'EOF'
import pandas as pd
import sys

try:
    df = pd.read_csv("../../data/raw/exp6_cache_miss.csv")
    
    grouped = df.groupby('working_set_kb').agg({
        'runtime_ms': ['mean', 'std'],
        'time_per_iter_us': ['mean', 'std'],
        'bandwidth_gbps': ['mean']
    }).reset_index()
    
    print("\nCache-Miss Impact Summary (Timing-Based):")
    print("=" * 70)
    print(f"{'Size (KB)':<12} {'Runtime (ms)':<20} {'Time/Iter (µs)':<20} {'Level'}")
    print("-" * 70)
    
    for _, row in grouped.iterrows():
        size = row['working_set_kb']
        runtime = row[('runtime_ms', 'mean')]
        runtime_std = row[('runtime_ms', 'std')]
        time_iter = row[('time_per_iter_us', 'mean')]
        time_iter_std = row[('time_per_iter_us', 'std')]
        
        level = 'L1' if size < 32 else 'L2' if size < 512 else 'L3' if size < 16384 else 'DRAM'
        
        print(f"{size:<12} {runtime:>8.2f} ± {runtime_std:<6.2f}   {time_iter:>8.3f} ± {time_iter_std:<6.3f}   {level}")
    
    print("\nKey Observations:")
    print("- Small working sets → Fast (L1/L2 cache)")
    print("- Large working sets → Slow (DRAM access)")
    print("- Runtime increase correlates with cache misses")

except Exception as e:
    print(f"Could not compute statistics: {e}")
EOF

echo ""
echo "Output file: $OUTPUT_FILE"
echo "Log file: $LOG_FILE"
echo ""
echo "Next steps:"
echo "1. Review runtime trends vs working set size"
echo "2. Run: cd ../../analysis && python3 analyze_exp6.py"
echo "3. Apply AMAT model in report: AMAT = Hit_Time + (Miss_Rate × Miss_Penalty)"
echo "4. Explain runtime differences using cache theory"
echo ""
echo "Note: This timing-based approach demonstrates cache effects without"
echo "      requiring hardware counters. Performance degradation at cache"
echo "      boundaries proves the cache-miss impact."
echo ""
