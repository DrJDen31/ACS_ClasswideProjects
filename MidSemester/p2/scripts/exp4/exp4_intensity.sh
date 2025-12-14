#!/bin/bash
# Experiment 4: Intensity Sweep (Throughput-Latency Trade-off)
# Demonstrates queuing effects and identifies the "knee" point
# Points: 60 (20 + 15 + 15 + 10) - HIGHEST VALUE

set -e
set -u

# Configuration
MLC_PATH="../../tools/mlc"
OUTPUT_DIR="../../data/raw"
OUTPUT_FILE="$OUTPUT_DIR/exp4_intensity.csv"
LOG_FILE="$OUTPUT_DIR/exp4_intensity.log"
REPETITIONS=${1:-3}

echo "========================================"
echo "Experiment 4: Intensity Sweep"
echo "HIGHEST VALUE: 60 points"
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
echo ""
echo "This experiment measures throughput-latency trade-off"
echo "Goal: Identify the 'knee' point using Little's Law"
echo ""

# Initialize CSV
echo "run,inject_delay,latency_ns,bandwidth_mbps,concurrency,notes" > "$OUTPUT_FILE"

echo "Running Loaded Latency Sweep (Intensity Sweep)..."
echo "This will test multiple injection rates from light to heavy load"
echo ""

for ((run=1; run<=REPETITIONS; run++)); do
    echo "========================================"
    echo "Run $run of $REPETITIONS"
    echo "========================================"
    
    # Run MLC loaded latency test
    echo "Running MLC loaded latency test..."
    $MLC_PATH --loaded_latency 2>&1 | tee temp_mlc_output.txt
    
    # Parse the loaded latency table
    # Look for lines like: "00000  1030.49   22964.8"
    
    # Extract data between "Inject  Latency Bandwidth" and "cache-to-cache"
    awk '
    /Inject.*Latency.*Bandwidth/ { in_table=1; next }
    /cache-to-cache/ { in_table=0 }
    in_table && /^[[:space:]]*[0-9]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+/ {
        print $0
    }
    ' temp_mlc_output.txt | while read -r line; do
        delay=$(echo "$line" | awk '{print $1}')
        latency=$(echo "$line" | awk '{print $2}')
        bandwidth=$(echo "$line" | awk '{print $3}')
        
        # Calculate concurrency using Little's Law
        # Concurrency = Throughput * Latency
        concurrency=$(echo "scale=2; ($bandwidth * $latency) / 1000000" | bc)
        
        echo "$run,$delay,$latency,$bandwidth,$concurrency,Loaded latency sweep" >> "$OUTPUT_FILE"
        echo "  ✓ Delay=$delay : Latency=$latency ns, BW=$bandwidth MB/s"
    done
    
    echo ""
    
    # Delay between runs
    if [ $run -lt $REPETITIONS ]; then
        sleep 5
    fi
done

# Clean up
rm -f temp_mlc_output.txt

echo ""
echo "========================================"
echo "Experiment 4 Complete!"
echo "========================================"
echo ""

# Compute statistics
echo "Computing statistics..."
python3 << 'EOF'
import pandas as pd
import numpy as np
import sys

try:
    df = pd.read_csv("../../data/raw/exp4_intensity.csv")
    
    # Group by injection delay
    grouped = df.groupby('inject_delay').agg({
        'latency_ns': ['mean', 'std'],
        'bandwidth_mbps': ['mean', 'std']
    }).reset_index()
    
    print("\nThroughput-Latency Trade-off Summary:")
    print("=" * 80)
    print(f"{'Delay':<10} {'Latency (ns)':<20} {'Bandwidth (MB/s)':<20} {'Intensity'}")
    print("-" * 80)
    
    for _, row in grouped.iterrows():
        delay = row['inject_delay']
        lat_mean = row[('latency_ns', 'mean')]
        lat_std = row[('latency_ns', 'std')]
        bw_mean = row[('bandwidth_mbps', 'mean')]
        bw_std = row[('bandwidth_mbps', 'std')]
        
        if delay < 100:
            intensity = "Heavy"
        elif delay < 1000:
            intensity = "Medium"
        else:
            intensity = "Light"
        
        print(f"{delay:<10} {lat_mean:>8.1f} ± {lat_std:<6.1f}   {bw_mean:>8.1f} ± {bw_std:<6.1f}   {intensity}")
    
    # Find approximate knee
    # Knee is where latency starts rising significantly while bandwidth plateaus
    # Simple heuristic: point where latency > 2x minimum latency and BW > 90% max
    min_lat = grouped[('latency_ns', 'mean')].min()
    max_bw = grouped[('bandwidth_mbps', 'mean')].max()
    
    knee_candidates = grouped[
        (grouped[('latency_ns', 'mean')] < 2 * min_lat) &
        (grouped[('bandwidth_mbps', 'mean')] > 0.9 * max_bw)
    ]
    
    if len(knee_candidates) > 0:
        knee = knee_candidates.iloc[-1]
        print("\n" + "=" * 80)
        print("Approximate 'Knee' Point (for initial analysis):")
        print(f"  Delay: {knee['inject_delay']}")
        print(f"  Latency: {knee[('latency_ns', 'mean')]:.1f} ns")
        print(f"  Bandwidth: {knee[('bandwidth_mbps', 'mean')]:.1f} MB/s")
        print(f"  % of Peak BW: {(knee[('bandwidth_mbps', 'mean')] / max_bw * 100):.1f}%")
        print("\nNote: Refine this analysis with analyze_exp4.py for accurate results")
    
except Exception as e:
    print(f"Could not compute statistics: {e}", file=sys.stderr)
EOF

echo ""
echo "Output file: $OUTPUT_FILE"
echo "Log file: $LOG_FILE"
echo ""
echo "Critical Analysis Steps:"
echo "1. Identify the 'knee' point on throughput-latency curve"
echo "2. Calculate % of theoretical peak bandwidth"
echo "3. Apply Little's Law to validate results"
echo "4. Discuss diminishing returns beyond knee"
echo ""
echo "Next step:"
echo "  cd ../../analysis && python3 analyze_exp4.py"
echo ""
echo "This is worth 60 points - the highest value experiment!"
echo "Make sure to thoroughly analyze and document findings."
echo ""
