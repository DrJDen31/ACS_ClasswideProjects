#!/bin/bash

# Benchmark automation script for Project A4
# Runs comprehensive benchmarks across all configurations

set -e  # Exit on error

echo "========================================"
echo "Project A4 Benchmark Suite"
echo "========================================"
echo "Start time: $(date)"
echo ""

# Configuration
STRATEGIES=("coarse" "fine")  # Add "rwlock" when implemented
WORKLOADS=("lookup" "insert" "mixed")
THREAD_COUNTS=(1 2 4 8 16)
DATASET_SIZES=(10000 100000 1000000)
REPETITIONS=5

RESULTS_DIR="../results/raw"
BENCHMARK_BIN="./benchmark"

# Check if benchmark binary exists
if [ ! -f "$BENCHMARK_BIN" ]; then
    echo "Error: Benchmark binary not found. Run 'make' first."
    exit 1
fi

# Create results directory
mkdir -p "$RESULTS_DIR"

# System info
echo "System Information:"
echo "  Hostname: $(hostname)"
echo "  CPU: $(lscpu | grep 'Model name' | cut -d ':' -f2 | xargs)"
echo "  Cores: $(nproc)"
echo "  Date: $(date)"
echo ""

# Warning about system state
echo "⚠ WARNING: For best results:"
echo "  1. Close all unnecessary applications"
echo "  2. Set CPU governor to 'performance' mode"
echo "  3. Ensure system is idle"
echo ""
read -p "Press Enter to continue or Ctrl+C to abort..."
echo ""

# Total configurations
total_configs=$((${#STRATEGIES[@]} * ${#WORKLOADS[@]} * ${#THREAD_COUNTS[@]} * ${#DATASET_SIZES[@]} * REPETITIONS))
current_config=0

echo "Running $total_configs benchmark configurations..."
echo "This may take a while. Progress will be shown below."
echo ""

# Main benchmark loop
for strategy in "${STRATEGIES[@]}"; do
    for workload in "${WORKLOADS[@]}"; do
        for threads in "${THREAD_COUNTS[@]}"; do
            for size in "${DATASET_SIZES[@]}"; do
                for rep in $(seq 1 $REPETITIONS); do
                    ((current_config++))
                    
                    output_file="${RESULTS_DIR}/${strategy}_${workload}_t${threads}_n${size}_rep${rep}.csv"
                    
                    echo -n "[$current_config/$total_configs] "
                    echo -n "strategy=$strategy workload=$workload threads=$threads size=$size rep=$rep... "
                    
                    # Run with perf if available
                    if command -v perf &> /dev/null; then
                        perf stat -e cycles,instructions,LLC-load-misses,LLC-store-misses \
                            -o "${output_file}.perf" \
                            "$BENCHMARK_BIN" \
                                --strategy "$strategy" \
                                --workload "$workload" \
                                --threads "$threads" \
                                --size "$size" \
                                > "$output_file" 2>&1
                    else
                        # Run without perf
                        "$BENCHMARK_BIN" \
                            --strategy "$strategy" \
                            --workload "$workload" \
                            --threads "$threads" \
                            --size "$size" \
                            > "$output_file" 2>&1
                    fi
                    
                    echo "✓"
                done
            done
        done
    done
done

echo ""
echo "========================================"
echo "Benchmark suite completed!"
echo "End time: $(date)"
echo "Results saved to: $RESULTS_DIR"
echo ""
echo "Next steps:"
echo "  1. Review results: ls -lh $RESULTS_DIR"
echo "  2. Generate plots: cd ../scripts && python analyze.py"
echo "========================================"
