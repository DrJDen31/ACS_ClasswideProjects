#!/usr/bin/env bash
set -euo pipefail

# Run all B2 analysis/plot scripts to regenerate plots from existing results.
# Usage (from inside WSL):
#   cd "$(dirname "$0")/.."  # go to TrackB project root
#   ./scripts/run_all_plots.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

run_analysis() {
  local exp_dir="$1"      # e.g., experiments/Experiment1_DRAM_Baseline
  local analyze_py="$2"   # e.g., analyze_experiment1.py
  echo
  echo "=== Analyzing ${exp_dir} with ${analyze_py} ==="
  (cd "${PROJECT_DIR}" && python "${exp_dir}/scripts/${analyze_py}")
}

# Analysis / plotting for Experiments 0–12
run_analysis "experiments/Experiment0_HNSWLIB_Baseline" "analyze_experiment0.py"
run_analysis "experiments/Experiment1_DRAM_Baseline" "analyze_experiment1.py"
run_analysis "experiments/Experiment2_Tiered_vs_DRAM" "analyze_experiment2.py"
run_analysis "experiments/Experiment3_Cache_Policies" "analyze_experiment3.py"
run_analysis "experiments/Experiment4_IO_Amplification" "analyze_experiment4.py"
run_analysis "experiments/Experiment5_SSD_Sensitivity" "analyze_experiment5.py"
run_analysis "experiments/Experiment6_Cost_Performance" "analyze_experiment6.py"
run_analysis "experiments/Experiment7_Scaling" "analyze_experiment7.py"
run_analysis "experiments/Experiment8_Compare_SOTA" "analyze_experiment8.py"
run_analysis "experiments/Experiment9_AnnSSD_vs_Tiered_vs_DRAM" "analyze_experiment9.py"
run_analysis "experiments/Experiment10_AnnSSD_Design_Space" "analyze_experiment10.py"
run_analysis "experiments/Experiment11_AnnSSD_Hardware_Levels" "analyze_experiment11.py"
run_analysis "experiments/Experiment12_Unified_Comparison" "analyze_experiment12.py"

echo
echo "=== All analysis plots completed ==="
