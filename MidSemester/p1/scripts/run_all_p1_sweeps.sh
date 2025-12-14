#!/usr/bin/env bash
# Project #1 — Master script to run all P1 sweeps
#
# This script:
# 1. Builds the project (Release mode)
# 2. Runs all non-stride sweeps (saxpy, dot, mul, stencil)
# 3. Runs all stride sweeps (saxpy, dot, mul, stencil)
# 4. Optionally generates plots
#
# Usage:
#   bash scripts/p1/run_all_p1_sweeps.sh [--plot]
#
# Options:
#   --plot    Generate all plots after sweeps complete
#
# Output:
#   CSV files in data/raw/
#   PNG plots in plots/p1/ (if --plot is specified)

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
BUILD_DIR="${ROOT_DIR}/build"
PLOT_FLAG=0

# Parse arguments
for arg in "$@"; do
  case $arg in
    --plot)
      PLOT_FLAG=1
      shift
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

echo "========================================"
echo "Project #1 — Master Sweep Script"
echo "========================================"
echo

# Step 1: Build the project
echo "[1/3] Building project (Release mode)..."
if [[ ! -f "${BUILD_DIR}/build.ninja" && ! -f "${BUILD_DIR}/Makefile" ]]; then
  cmake -S "${ROOT_DIR}" -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE=Release
fi
cmake --build "${BUILD_DIR}" -j
echo "Build complete."
echo

# Step 2: Run non-stride sweeps
echo "[2/3] Running non-stride sweeps (saxpy, dot, mul, stencil)..."
bash "${ROOT_DIR}/scripts/p1/run_saxpy_sweep.sh"
bash "${ROOT_DIR}/scripts/p1/run_dot_sweep.sh"
bash "${ROOT_DIR}/scripts/p1/run_mul_sweep.sh"
bash "${ROOT_DIR}/scripts/p1/run_stencil_sweep.sh"
echo "Non-stride sweeps complete."
echo

# Step 3: Run stride sweeps
echo "[3/3] Running stride sweeps (saxpy, dot, mul, stencil)..."
bash "${ROOT_DIR}/scripts/p1/run_saxpy_stride_sweep.sh"
bash "${ROOT_DIR}/scripts/p1/run_dot_stride_sweep.sh"
bash "${ROOT_DIR}/scripts/p1/run_mul_stride_sweep.sh"
bash "${ROOT_DIR}/scripts/p1/run_stencil_stride_sweep.sh"
echo "Stride sweeps complete."
echo

echo "========================================"
echo "All sweeps completed successfully!"
echo "CSV outputs: ${ROOT_DIR}/data/raw/"
echo "========================================"
echo

# Step 4: Generate plots (optional)
if [[ $PLOT_FLAG -eq 1 ]]; then
  echo "Generating plots..."
  
  # Define plot configurations
  # Format: "INPUT_CSV OUTPUT_PNG XAXIS [EXTRA_ARGS]"
  PLOT_CONFIGS=(
    # Non-stride plots (vs N)
    "data/raw/p1_saxpy.csv plots/p1/saxpy_vs_n.png n"
    "data/raw/p1_dot.csv plots/p1/dot_vs_n.png n"
    "data/raw/p1_mul.csv plots/p1/mul_vs_n.png n"
    "data/raw/p1_stencil.csv plots/p1/stencil_vs_n.png n"
    
    # Stride plots (vs stride at N=2^20)
    "data/raw/p1_saxpy_stride.csv plots/p1/saxpy_vs_stride.png stride --fixed_n 1048576"
    "data/raw/p1_dot_stride.csv plots/p1/dot_vs_stride.png stride --fixed_n 1048576"
    "data/raw/p1_mul_stride.csv plots/p1/mul_vs_stride.png stride --fixed_n 1048576"
    "data/raw/p1_stencil_stride.csv plots/p1/stencil_vs_stride.png stride --fixed_n 1048576"
  )
  
  for config in "${PLOT_CONFIGS[@]}"; do
    read -r input output xaxis extra <<< "$config"
    input_full="${ROOT_DIR}/${input}"
    output_full="${ROOT_DIR}/${output}"
    
    if [[ -f "$input_full" ]]; then
      echo "  - Plotting: $output"
      python3 "${ROOT_DIR}/scripts/p1/plot_p1.py" --in "$input_full" --out "$output_full" --xaxis "$xaxis" $extra
    else
      echo "  - Skipping: $input (file not found)"
    fi
  done
  
  echo
  echo "========================================"
  echo "Plots generated: ${ROOT_DIR}/plots/p1/"
  echo "========================================"
fi

echo
echo "Done!"
