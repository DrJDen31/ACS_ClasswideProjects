#!/bin/bash
# Experiment 7: TLB-Miss Impact (Timing-Only Version)
# Shows TLB effects through runtime measurements
# Points: 25 (20-23 achievable without hardware counters)

set -e
set -u

# Configuration
KERNEL_PATH="../../bin/tlb_miss_kernel"
OUTPUT_DIR="../../data/raw"
OUTPUT_FILE="$OUTPUT_DIR/exp7_tlb_miss.csv"
LOG_FILE="$OUTPUT_DIR/exp7_tlb_miss.log"
REPETITIONS=${1:-5}

# Test configuration
TOTAL_SIZE_MB=100
PAGE_STRIDE_KB=4
ITERATIONS=1000

echo "========================================"
echo "Experiment 7: TLB-Miss Impact"
echo "Timing-Only Version (No Hardware Counters)"
echo "========================================"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Start logging
exec > >(tee "$LOG_FILE") 2>&1

echo "Configuration:"
echo "  Kernel: $KERNEL_PATH"
echo "  Total Size: $TOTAL_SIZE_MB MB"
echo "  Page Stride: $PAGE_STRIDE_KB KB"
echo "  Iterations: $ITERATIONS"
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

# Check for huge pages (optional)
if [ -f /proc/meminfo ]; then
    HUGEPAGES=$(grep HugePages_Total /proc/meminfo | awk '{print $2}')
    if [ "$HUGEPAGES" = "0" ] || [ -z "$HUGEPAGES" ]; then
        echo "⚠ WARNING: No huge pages allocated"
        echo "For best results, allocate huge pages:"
        echo "  echo 512 | sudo tee /proc/sys/vm/nr_hugepages"
        echo ""
        echo "The experiment will still run and show performance differences"
        echo ""
        CAN_TEST_HUGEPAGES=false
    else
        echo "✓ Huge pages available: $HUGEPAGES"
        CAN_TEST_HUGEPAGES=true
    fi
else
    CAN_TEST_HUGEPAGES=false
fi

echo ""

# Initialize CSV
echo "run,use_large_pages,runtime_ms,time_per_iter_us,pages_per_sec,bandwidth_gbps" > "$OUTPUT_FILE"

echo "Running TLB-Miss Impact Experiment..."
echo ""

# Phase 1: Standard 4KB Pages
echo "========================================"
echo "Phase 1: Standard 4KB Pages"
echo "========================================"

test_num=0
total_tests=$((REPETITIONS * 2))

for ((run=1; run<=REPETITIONS; run++)); do
    test_num=$((test_num + 1))
    echo "[$test_num/$total_tests] Run $run/$REPETITIONS - 4KB pages"
    
    # Run with standard pages
    output=$($KERNEL_PATH $TOTAL_SIZE_MB $PAGE_STRIDE_KB $ITERATIONS 0 2>&1)
    
    # Parse output
    total_time_s=$(echo "$output" | grep "Total Time:" | grep -oE '[0-9.]+' | head -n1)
    time_per_iter_us=$(echo "$output" | grep "Time per Iteration:" | grep -oE '[0-9.]+' | head -n1)
    pages_per_sec=$(echo "$output" | grep "Pages per Second:" | grep -oE '[0-9.]+' | head -n1)
    bandwidth_gbps=$(echo "$output" | grep "Bandwidth:" | grep -oE '[0-9.]+' | head -n1)
    
    # Calculate runtime in ms
    if [ -n "$total_time_s" ]; then
        runtime_ms=$(echo "scale=3; $total_time_s * 1000" | bc)
    else
        runtime_ms="0"
    fi
    
    # Use defaults if parsing failed
    time_per_iter_us=${time_per_iter_us:-0}
    pages_per_sec=${pages_per_sec:-0}
    bandwidth_gbps=${bandwidth_gbps:-0}
    
    # Save to CSV
    echo "$run,0,$runtime_ms,$time_per_iter_us,$pages_per_sec,$bandwidth_gbps" >> "$OUTPUT_FILE"
    
    echo "  Runtime: ${runtime_ms} ms"
    echo "  Time/iter: ${time_per_iter_us} µs"
    echo ""
    
    sleep 0.5
done

# Phase 2: Huge Pages (2MB)
echo "========================================"
echo "Phase 2: Huge Pages (2MB)"
echo "========================================"

if [ "$CAN_TEST_HUGEPAGES" = false ]; then
    echo "⚠ Skipping huge page tests (not allocated)"
    echo "To enable huge pages:"
    echo "  echo 512 | sudo tee /proc/sys/vm/nr_hugepages"
else
    for ((run=1; run<=REPETITIONS; run++)); do
        test_num=$((test_num + 1))
        echo "[$test_num/$total_tests] Run $run/$REPETITIONS - 2MB huge pages"
        
        # Run with huge pages
        output=$($KERNEL_PATH $TOTAL_SIZE_MB $PAGE_STRIDE_KB $ITERATIONS 1 2>&1)
        
        # Parse output
        total_time_s=$(echo "$output" | grep "Total Time:" | grep -oE '[0-9.]+' | head -n1)
        time_per_iter_us=$(echo "$output" | grep "Time per Iteration:" | grep -oE '[0-9.]+' | head -n1)
        pages_per_sec=$(echo "$output" | grep "Pages per Second:" | grep -oE '[0-9.]+' | head -n1)
        bandwidth_gbps=$(echo "$output" | grep "Bandwidth:" | grep -oE '[0-9.]+' | head -n1)
        
        # Calculate runtime in ms
        if [ -n "$total_time_s" ]; then
            runtime_ms=$(echo "scale=3; $total_time_s * 1000" | bc)
        else
            runtime_ms="0"
        fi
        
        # Use defaults if parsing failed
        time_per_iter_us=${time_per_iter_us:-0}
        pages_per_sec=${pages_per_sec:-0}
        bandwidth_gbps=${bandwidth_gbps:-0}
        
        # Save to CSV
        echo "$run,1,$runtime_ms,$time_per_iter_us,$pages_per_sec,$bandwidth_gbps" >> "$OUTPUT_FILE"
        
        echo "  Runtime: ${runtime_ms} ms"
        echo "  Time/iter: ${time_per_iter_us} µs"
        echo ""
        
        sleep 0.5
    done
fi

echo ""
echo "========================================"
echo "Experiment 7 Complete!"
echo "========================================"
echo ""

# Compute statistics
echo "Computing statistics..."
python3 << 'EOF'
import pandas as pd
import sys

try:
    df = pd.read_csv("../../data/raw/exp7_tlb_miss.csv")
    
    grouped = df.groupby('use_large_pages').agg({
        'runtime_ms': ['mean', 'std'],
        'time_per_iter_us': ['mean'],
        'bandwidth_gbps': ['mean']
    }).reset_index()
    
    print("\nTLB-Miss Impact Summary (Timing-Based):")
    print("=" * 70)
    print(f"{'Page Type':<20} {'Runtime (ms)':<25} {'Time/Iter (µs)'}")
    print("-" * 70)
    
    for _, row in grouped.iterrows():
        page_type = '2MB Huge Pages' if row['use_large_pages'] == 1 else '4KB Standard'
        runtime = row[('runtime_ms', 'mean')]
        runtime_std = row[('runtime_ms', 'std')]
        time_iter = row[('time_per_iter_us', 'mean')]
        
        print(f"{page_type:<20} {runtime:>10.2f} ± {runtime_std:<8.2f}   {time_iter:>10.3f}")
    
    if len(grouped) == 2:
        std_runtime = grouped[grouped['use_large_pages']==0][('runtime_ms', 'mean')].values[0]
        large_runtime = grouped[grouped['use_large_pages']==1][('runtime_ms', 'mean')].values[0]
        speedup = (std_runtime / large_runtime - 1) * 100
        
        print(f"\nPerformance improvement with huge pages: {speedup:+.1f}%")
        print("\nKey Observations:")
        print("- 4KB pages → More TLB misses → Slower")
        print("- 2MB pages → Fewer TLB misses → Faster")
        print("- Runtime difference demonstrates TLB impact")

except Exception as e:
    print(f"Could not compute statistics: {e}")
EOF

echo ""
echo "Output file: $OUTPUT_FILE"
echo "Log file: $LOG_FILE"
echo ""
echo "Next steps:"
echo "1. Review runtime differences between page sizes"
echo "2. Run: cd ../../analysis && python3 analyze_exp7.py"
echo "3. Calculate DTLB reach: 64 entries × 4KB = 256KB vs 64 × 2MB = 128MB"
echo "4. Explain performance differences using TLB theory"
echo ""
echo "Note: This timing-based approach demonstrates TLB effects without"
echo "      requiring hardware counters. Performance improvement with huge"
echo "      pages proves the TLB-miss impact."
echo ""
