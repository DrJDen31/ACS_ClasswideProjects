#!/bin/bash
# Experiment 7: TLB-Miss Impact
# Measures TLB miss effects and huge page benefits
# Points: 25 (10 + 10 + 5)
# Requires: Linux/WSL with perf and huge pages

set -e
set -u

# Configuration
KERNEL_PATH="../../bin/tlb_miss_kernel"
OUTPUT_DIR="../../data/raw"
OUTPUT_FILE="$OUTPUT_DIR/exp7_tlb_miss.csv"
LOG_FILE="$OUTPUT_DIR/exp7_tlb_miss.log"
REPETITIONS=${1:-5}

# Test configurations
TOTAL_SIZE_MB=100  # Total memory to test
PAGE_STRIDE_KB=4   # 4KB stride to touch many pages
ITERATIONS=1000

echo "========================================"
echo "Experiment 7: TLB-Miss Impact"
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
    echo ""
fi

# Check huge pages
echo "Huge Pages Configuration:"
if [ -f /proc/meminfo ]; then
    grep -i huge /proc/meminfo
    
    HUGEPAGES=$(grep HugePages_Total /proc/meminfo | awk '{print $2}')
    if [ "$HUGEPAGES" = "0" ] || [ -z "$HUGEPAGES" ]; then
        echo ""
        echo "⚠ WARNING: No huge pages allocated!"
        echo "To allocate huge pages for this experiment:"
        echo "  echo 512 | sudo tee /proc/sys/vm/nr_hugepages"
        echo ""
        echo "The experiment will run but won't test huge pages."
        echo ""
        CAN_TEST_HUGEPAGES=false
    else
        echo ""
        echo "✓ Huge pages available: $HUGEPAGES"
        CAN_TEST_HUGEPAGES=true
    fi
else
    CAN_TEST_HUGEPAGES=false
fi

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

# Initialize CSV
echo "run,use_hugepages,runtime_ms,dtlb_load_misses,dtlb_loads,miss_rate_pct,itlb_misses,page_faults,instructions,cycles,ipc" > "$OUTPUT_FILE"

echo "Running TLB-Miss Impact Experiment..."
echo ""

# Test with standard 4KB pages
echo "========================================"
echo "Phase 1: Standard 4KB Pages"
echo "========================================"

test_num=0
for ((run=1; run<=REPETITIONS; run++)); do
    test_num=$((test_num + 1))
    echo "[$test_num/$(( $REPETITIONS * 2 ))] Run $run/$REPETITIONS - 4KB pages"
    
    # Run with perf
    perf_output=$(perf stat -e dTLB-load-misses,dTLB-loads,iTLB-load-misses,page-faults,instructions,cycles \
        $KERNEL_PATH $TOTAL_SIZE_MB $PAGE_STRIDE_KB $ITERATIONS 0 2>&1)
    
    # Parse kernel output
    runtime_s=$(echo "$perf_output" | grep "Total Time:" | grep -oE '[0-9.]+' | head -n1)
    runtime_ms=$(echo "scale=3; $runtime_s * 1000" | bc)
    
    # Parse perf output
    dtlb_load_misses=$(echo "$perf_output" | grep "dTLB-load-misses" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
    dtlb_loads=$(echo "$perf_output" | grep "dTLB-loads" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
    itlb_misses=$(echo "$perf_output" | grep "iTLB-load-misses" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
    page_faults=$(echo "$perf_output" | grep "page-faults" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
    instructions=$(echo "$perf_output" | grep "instructions" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
    cycles=$(echo "$perf_output" | grep -E "^\s*[0-9,]+\s+cycles" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
    
    # Calculate miss rate
    if [ -n "$dtlb_loads" ] && [ "$dtlb_loads" -gt 0 ]; then
        miss_rate=$(echo "scale=4; ($dtlb_load_misses / $dtlb_loads) * 100" | bc)
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
    echo "$run,0,$runtime_ms,$dtlb_load_misses,$dtlb_loads,$miss_rate,$itlb_misses,$page_faults,$instructions,$cycles,$ipc" >> "$OUTPUT_FILE"
    
    echo "  Runtime: ${runtime_ms} ms"
    echo "  DTLB Miss Rate: ${miss_rate}%"
    echo "  DTLB Misses: $dtlb_load_misses"
    echo "  IPC: $ipc"
    echo ""
    
    sleep 1
done

# Test with huge pages (if available)
if [ "$CAN_TEST_HUGEPAGES" = true ]; then
    echo "========================================"
    echo "Phase 2: Huge Pages (2MB)"
    echo "========================================"
    
    for ((run=1; run<=REPETITIONS; run++)); do
        test_num=$((test_num + 1))
        echo "[$test_num/$(( $REPETITIONS * 2 ))] Run $run/$REPETITIONS - 2MB huge pages"
        
        # Run with huge pages (use_hugepages=1)
        perf_output=$(perf stat -e dTLB-load-misses,dTLB-loads,iTLB-load-misses,page-faults,instructions,cycles \
            $KERNEL_PATH $TOTAL_SIZE_MB $PAGE_STRIDE_KB $ITERATIONS 1 2>&1)
        
        # Parse outputs (same as above)
        runtime_s=$(echo "$perf_output" | grep "Total Time:" | grep -oE '[0-9.]+' | head -n1)
        runtime_ms=$(echo "scale=3; $runtime_s * 1000" | bc)
        
        dtlb_load_misses=$(echo "$perf_output" | grep "dTLB-load-misses" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
        dtlb_loads=$(echo "$perf_output" | grep "dTLB-loads" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
        itlb_misses=$(echo "$perf_output" | grep "iTLB-load-misses" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
        page_faults=$(echo "$perf_output" | grep "page-faults" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
        instructions=$(echo "$perf_output" | grep "instructions" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
        cycles=$(echo "$perf_output" | grep -E "^\s*[0-9,]+\s+cycles" | grep -oE '[0-9,]+' | head -n1 | tr -d ',')
        
        if [ -n "$dtlb_loads" ] && [ "$dtlb_loads" -gt 0 ]; then
            miss_rate=$(echo "scale=4; ($dtlb_load_misses / $dtlb_loads) * 100" | bc)
        else
            miss_rate="0"
        fi
        
        if [ -n "$cycles" ] && [ "$cycles" -gt 0 ]; then
            ipc=$(echo "scale=3; $instructions / $cycles" | bc)
        else
            ipc="0"
        fi
        
        echo "$run,1,$runtime_ms,$dtlb_load_misses,$dtlb_loads,$miss_rate,$itlb_misses,$page_faults,$instructions,$cycles,$ipc" >> "$OUTPUT_FILE"
        
        echo "  Runtime: ${runtime_ms} ms"
        echo "  DTLB Miss Rate: ${miss_rate}%"
        echo "  DTLB Misses: $dtlb_load_misses"
        echo "  IPC: $ipc"
        echo ""
        
        sleep 1
    done
else
    echo "Skipping huge pages test (not allocated)"
fi

echo ""
echo "========================================"
echo "Experiment 7 Complete!"
echo "========================================"
echo ""

# Compute statistics and comparison
echo "Computing statistics..."
python3 << 'EOF'
import pandas as pd
import numpy as np
import sys

try:
    df = pd.read_csv("../../data/raw/exp7_tlb_miss.csv")
    
    # Group by page type
    grouped = df.groupby('use_hugepages').agg({
        'runtime_ms': ['mean', 'std'],
        'miss_rate_pct': ['mean', 'std'],
        'dtlb_load_misses': ['mean'],
        'ipc': ['mean']
    }).reset_index()
    
    print("\nTLB-Miss Impact Summary:")
    print("=" * 90)
    print(f"{'Page Type':<15} {'Runtime (ms)':<20} {'Miss Rate (%)':<20} {'IPC':<10}")
    print("-" * 90)
    
    for _, row in grouped.iterrows():
        page_type = "2MB Huge Pages" if row['use_hugepages'] == 1 else "4KB Standard"
        runtime = row[('runtime_ms', 'mean')]
        runtime_std = row[('runtime_ms', 'std')]
        miss_rate = row[('miss_rate_pct', 'mean')]
        miss_rate_std = row[('miss_rate_pct', 'std')]
        ipc = row[('ipc', 'mean')]
        
        print(f"{page_type:<15} {runtime:>8.2f} ± {runtime_std:<6.2f}   {miss_rate:>8.4f} ± {miss_rate_std:<6.4f}   {ipc:>6.3f}")
    
    # Compare standard vs huge pages
    if len(grouped) == 2:
        std_runtime = grouped[grouped['use_hugepages'] == 0][('runtime_ms', 'mean')].values[0]
        huge_runtime = grouped[grouped['use_hugepages'] == 1][('runtime_ms', 'mean')].values[0]
        speedup = (std_runtime / huge_runtime - 1) * 100
        
        std_misses = grouped[grouped['use_hugepages'] == 0][('miss_rate_pct', 'mean')].values[0]
        huge_misses = grouped[grouped['use_hugepages'] == 1][('miss_rate_pct', 'mean')].values[0]
        miss_reduction = ((std_misses - huge_misses) / std_misses) * 100
        
        print("\n" + "=" * 90)
        print("HUGE PAGE BENEFIT")
        print("=" * 90)
        print(f"  Performance improvement: {speedup:+.1f}%")
        print(f"  TLB miss reduction: {miss_reduction:.1f}%")
        print(f"  Conclusion: {'Significant' if speedup > 10 else 'Moderate' if speedup > 5 else 'Minor'} benefit from huge pages")
    
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
echo "1. Review TLB miss rate differences"
echo "2. Run: cd ../../analysis && python3 analyze_exp7.py"
echo "3. Calculate DTLB reach for both page sizes"
echo "4. Discuss performance impact and huge page benefits"
echo ""
