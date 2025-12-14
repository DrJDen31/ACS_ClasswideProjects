#!/usr/bin/env bash
set -euo pipefail

# Run all B2 experiments (0–12) to regenerate raw JSON results.
# Usage (from inside WSL):
#   cd "$(dirname "$0")/.."  # go to TrackB project root
#   ./scripts/run_all_experiments.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

run_experiment() {
  local exp_dir="$1"      # e.g., experiments/Experiment1_DRAM_Baseline
  local script_name="$2"  # e.g., experiment1.sh
  echo
  echo "=== Running ${exp_dir}/scripts/${script_name} ==="
  (cd "${PROJECT_DIR}/${exp_dir}" && ./scripts/"${script_name}")
}

# ---------------------------------------------------------------------------
# Experiment 0–7: DRAM/tiered baseline and supporting studies
# ---------------------------------------------------------------------------
run_experiment "experiments/Experiment0_HNSWLIB_Baseline" "experiment0.sh"
run_experiment "experiments/Experiment1_DRAM_Baseline" "experiment1.sh"
run_experiment "experiments/Experiment2_Tiered_vs_DRAM" "experiment2.sh"
run_experiment "experiments/Experiment3_Cache_Policies" "experiment3.sh"
run_experiment "experiments/Experiment4_IO_Amplification" "experiment4.sh"
run_experiment "experiments/Experiment5_SSD_Sensitivity" "experiment5.sh"
run_experiment "experiments/Experiment6_Cost_Performance" "experiment6.sh"
run_experiment "experiments/Experiment7_Scaling" "experiment7.sh"

# ---------------------------------------------------------------------------
# Experiment 8–12: SOTA comparison, ANN-SSD design space and hardware levels,
# and unified cross-solution comparison.
# ---------------------------------------------------------------------------
run_experiment "experiments/Experiment8_Compare_SOTA" "experiment8.sh"
run_experiment "experiments/Experiment9_AnnSSD_vs_Tiered_vs_DRAM" "experiment9.sh"
run_experiment "experiments/Experiment10_AnnSSD_Design_Space" "experiment10.sh"
run_experiment "experiments/Experiment11_AnnSSD_Hardware_Levels" "experiment11.sh"
run_experiment "experiments/Experiment12_Unified_Comparison" "experiment12.sh"

echo
echo "=== All experiments completed ==="
