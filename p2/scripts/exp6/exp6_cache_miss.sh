#!/bin/bash
# Experiment 6: Cache-Miss Impact
# Correlates cache miss rate with kernel performance
# Points: 25 (10 + 10 + 5)
# Requires: Linux/WSL with perf

set -e
set -u

# Configuration
KERNEL_PATH="../../bin/cache_miss_kernel"
OUTPUT_DIR="../../data/raw"
OUTPUT_FILE="$OUTPUT_DIR/exp6_cache_miss.csv"
LOG_FILE="$OUTPUT_DIR/exp6_cache_miss.log"
REPETITIONS=${1:-5}

# Working set sizes to test (KB)
# Small = low miss rate, Large = high miss rate
WORKING_SETS=(16 64 256 1024 4096 16384 32768)
ITERATIONS=10000

echo "========================================"
echo "Experiment 6: Cache-Miss Impact"
echo "========================================"
echo ""

# Check for kernel
if [ ! -f "$KERNEL_PATH" ]; then
    echo "Error: Kernel not found at $KERNEL_PATH"
    echo "Build with:"
    echo "  cd ../../src && mkdir -p build && cd build"
    echo "  cmake .. && cmake --build ."
    exit 1
fi

if [ ! -x "$KERNEL_PATH" ]; then
    chmod +x "$KERNEL_PATH"
fi

# Check for perf
if ! command -v perf &> /dev/null; then
    echo "Error: perf not found. This experiment requires Linux/WSL with perf."
    echo "Install with: sudo apt-get install linux-tools-common linux-tools-generic"
    exit 1
fi

# Check perf access
PARANOID=$(cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null || echo "unknown")
if [ "$PARANOID" != "unknown" ] && [ "$PARANOID" -gt 1 ]; then
    echo "Warning: perf_event_paranoid = $PARANOID (restricted access)"
    echo "For full access, run: echo 1 | sudo tee /proc/sys/kernel/perf_event_paranoid"
    echo "Or run this script with sudo"
    echo ""
fi

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

# Initialize CSV
echo "run,working_set_kb,runtime_ms,cache_refs,cache_misses,miss_rate_pct,l1_misses,llc_misses,instructions,cycles,ipc" > "$OUTPUT_FILE"

echo "Running Cache-Miss Impact Experiment..."
total_tests=$((${#WORKING_SETS[@]} * REPETITIONS))
echo "Total tests: $total_tests"
echo ""

test_num=0

for size_kb in "${WORKING_SETS[@]}"; do
    echo "========================================"
    echo "Testing: ${size_kb} KB working set"
    echo "========================================"
    
    for ((run=1; run<=REPETITIONS; run++)); do
        test_num=$((test_num + 1))
        echo "[$test_num/$total_tests] Run $run/$REPETITIONS - ${size_kb} KB"
        
        # Run with perf
        perf_output=$(perf stat -e cache-references,cache-misses,L1-dcache-load-misses,LLC-load-misses,instructions,cycles \
            $KERNEL_PATH $size_kb $ITERATIONS 2>&1)
        
        # Parse kernel output
        runtime_ms=$(echo "$perf_output" | grep "Total Time:" | grep -oE '[0-9.]+' | head -n1)
        runtime_ms=$(echo "scale=3; $runtime_ms * 1000" | bc)  # Convert s to ms
        
        # Parse perf output
        cache_refs=$(echo "$perf_output" | grep "cache-references" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
        cache_misses=$(echo "$perf_output" | grep "cache-misses" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
        l1_misses=$(echo "$perf_output" | grep "L1-dcache-load-misses" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
        llc_misses=$(echo "$perf_output" | grep "LLC-load-misses" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
        instructions=$(echo "$perf_output" | grep "instructions" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
        cycles=$(echo "$perf_output" | grep -E "^\s*[0-9,]+\s+cycles" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
        
        # Calculate miss rate
        if [ -n "$cache_refs" ] && [ "$cache_refs" -gt 0 ]; then
            miss_rate=$(echo "scale=4; ($cache_misses / $cache_refs) * 100" | bc)
        else
            miss_rate="0"
        fi
        
        # Calculate IPC
        if [ -n "$cycles" ] && [ "$cycles" -gt 0 ]; then
            ipc=$(echo "scale=3; $instructions / $cycles" | bc)
        else
            ipc="0"
        fi
        
        # Save to CSV
        echo "$run,$size_kb,$runtime_ms,$cache_refs,$cache_misses,$miss_rate,$l1_misses,$llc_misses,$instructions,$cycles,$ipc" >> "$OUTPUT_FILE"
        
        echo "  Runtime: ${runtime_ms} ms"
        echo "  Cache Miss Rate: ${miss_rate}%"
        echo "  L1 Misses: $l1_misses"
        echo "  LLC Misses: $llc_misses"
        echo "  IPC: $ipc"
        echo ""
        
        sleep 1
    done
done

echo ""
echo "========================================"
echo "Experiment 6 Complete!"
echo "========================================"
echo ""

# Compute statistics and correlation
echo "Computing statistics and correlation..."
python3 << 'EOF'
import pandas as pd
import numpy as np
from scipy import stats
import sys

try:
    df = pd.read_csv("../../data/raw/exp6_cache_miss.csv")
    
    # Group by working set size
    grouped = df.groupby('working_set_kb').agg({
        'runtime_ms': ['mean', 'std'],
        'miss_rate_pct': ['mean', 'std'],
        'l1_misses': ['mean'],
        'llc_misses': ['mean'],
        'ipc': ['mean']
    }).reset_index()
    
    print("\nCache-Miss Impact Summary:")
    print("=" * 90)
    print(f"{'Size (KB)':<12} {'Runtime (ms)':<18} {'Miss Rate (%)':<18} {'IPC':<10}")
    print("-" * 90)
    
    for _, row in grouped.iterrows():
        size = row['working_set_kb']
        runtime = row[('runtime_ms', 'mean')]
        runtime_std = row[('runtime_ms', 'std')]
        miss_rate = row[('miss_rate_pct', 'mean')]
        miss_rate_std = row[('miss_rate_pct', 'std')]
        ipc = row[('ipc', 'mean')]
        
        print(f"{size:<12} {runtime:>7.2f} ± {runtime_std:<6.2f}   {miss_rate:>6.2f} ± {miss_rate_std:<6.2f}   {ipc:>6.3f}")
    
    # Correlation analysis
    print("\n" + "=" * 90)
    print("CORRELATION ANALYSIS")
    print("=" * 90)
    
    # Calculate correlation between miss rate and runtime
    miss_rates = grouped[('miss_rate_pct', 'mean')].values
    runtimes = grouped[('runtime_ms', 'mean')].values
    
    correlation, p_value = stats.pearsonr(miss_rates, runtimes)
    
    print(f"\nPearson Correlation (Miss Rate vs Runtime):")
    print(f"  r = {correlation:.4f}")
    print(f"  p-value = {p_value:.6f}")
    
    if abs(correlation) > 0.8:
        print(f"  Interpretation: Strong correlation - cache misses significantly impact performance")
    elif abs(correlation) > 0.5:
        print(f"  Interpretation: Moderate correlation - cache misses affect performance")
    else:
        print(f"  Interpretation: Weak correlation - other factors may dominate")
    
except Exception as e:
    print(f"Could not compute statistics: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
EOF

echo ""
echo "Output file: $OUTPUT_FILE"
echo "Log file: $LOG_FILE"
echo ""
echo "Next steps:"
echo "1. Review correlation between miss rate and runtime"
echo "2. Run: cd ../../analysis && python3 analyze_exp6.py"
echo "3. Apply AMAT model to explain performance degradation"
echo "4. Calculate effective memory access time"
echo ""
