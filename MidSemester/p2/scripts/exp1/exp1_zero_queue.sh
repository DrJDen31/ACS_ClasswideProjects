#!/bin/bash
# Experiment 1: Zero-Queue Baselines
# Measures single-access latency for L1, L2, L3, and DRAM
# Points: 30 (10 + 10 + 10)

set -e  # Exit on error
set -u  # Error on undefined variable

# Configuration
MLC_PATH="../tools/mlc"
OUTPUT_DIR="../data/raw"
OUTPUT_FILE="$OUTPUT_DIR/exp1_zero_queue.csv"
LOG_FILE="$OUTPUT_DIR/exp1_zero_queue.log"
REPETITIONS=${1:-5}

echo "========================================"
echo "Experiment 1: Zero-Queue Baselines"
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
echo "  CPU: $(grep "model name" /proc/cpuinfo | head -n1 | cut -d':' -f2 | xargs)"
echo ""

# Initialize CSV
echo "run,metric,value_ns,notes" > "$OUTPUT_FILE"

echo "Running Intel MLC idle latency measurements..."
echo "This measures zero-queue (single-access) latency"
echo ""

for ((run=1; run<=REPETITIONS; run++)); do
    echo "Run $run of $REPETITIONS..."
    
    # Run MLC idle latency
    $MLC_PATH --idle_latency 2>&1 | tee temp_mlc_output.txt
    
    # Parse the output - look for the latency value
    # Format: "       0         107.2"
    latency=$(grep -E '^\s+0\s+[0-9.]+' temp_mlc_output.txt | awk '{print $2}')
    
    if [ -n "$latency" ]; then
        echo "$run,DRAM_idle_latency,$latency,Measured with --idle_latency" >> "$OUTPUT_FILE"
        echo "  ✓ Captured: DRAM idle latency = $latency ns"
    else
        echo "  ⚠ Warning: Could not parse idle latency from output"
    fi
    
    # Small delay between runs
    sleep 2
done

echo ""
echo "========================================"
echo "Phase 1 Complete: Idle Latency"
echo "========================================"
echo ""

# Additional measurements for cache levels
echo "Running detailed latency measurements..."
echo ""

for ((run=1; run<=REPETITIONS; run++)); do
    echo "Detailed run $run of $REPETITIONS..."
    
    $MLC_PATH --latency_matrix 2>&1 | tee temp_mlc_output.txt
    
    # Parse L2-L2 latencies
    l2_hit=$(grep "L2->L2 HIT  latency" temp_mlc_output.txt | grep -oE '[0-9.]+' | head -n1)
    l2_hitm=$(grep "L2->L2 HITM latency" temp_mlc_output.txt | grep -oE '[0-9.]+' | head -n1)
    
    if [ -n "$l2_hit" ]; then
        echo "$run,L2_L2_latency,$l2_hit,L2-to-L2 transfer latency" >> "$OUTPUT_FILE"
        echo "  ✓ Captured: L2-L2 latency = $l2_hit ns"
    fi
    
    if [ -n "$l2_hitm" ]; then
        echo "$run,L2_L2_HITM_latency,$l2_hitm,L2-to-L2 HITM latency" >> "$OUTPUT_FILE"
        echo "  ✓ Captured: L2-L2 HITM latency = $l2_hitm ns"
    fi
    
    sleep 2
done

# Clean up temp file
rm -f temp_mlc_output.txt

echo ""
echo "========================================"
echo "Experiment 1 Complete!"
echo "========================================"
echo ""
echo "Output file: $OUTPUT_FILE"
echo "Log file: $LOG_FILE"
echo ""

# Calculate statistics
echo "Computing statistics..."
python3 << 'EOF'
import pandas as pd
import sys

try:
    df = pd.read_csv("../data/raw/exp1_zero_queue.csv")
    
    print("\nSummary Statistics:")
    print("=" * 60)
    
    for metric in df['metric'].unique():
        data = df[df['metric'] == metric]['value_ns']
        print(f"\n{metric}:")
        print(f"  Mean:   {data.mean():.2f} ns")
        print(f"  Median: {data.median():.2f} ns")
        print(f"  Std:    {data.std():.2f} ns")
        print(f"  Min:    {data.min():.2f} ns")
        print(f"  Max:    {data.max():.2f} ns")
        print(f"  CV:     {(data.std()/data.mean()*100):.2f}%")
        
except Exception as e:
    print(f"Could not compute statistics: {e}", file=sys.stderr)
EOF

echo ""
echo "Next steps:"
echo "1. Review the CSV file for collected latencies"
echo "2. Check coefficient of variation (CV) - should be <5%"
echo "3. Generate latency table for report"
echo ""
echo "Note: MLC provides limited cache-level breakdown on some CPUs."
echo "For more detailed L1/L2/L3 latencies, consider using:"
echo "  - Custom pointer-chasing benchmark"
echo "  - lmbench: lat_mem_rd command"
echo "  - CPU specification sheets"
echo ""
