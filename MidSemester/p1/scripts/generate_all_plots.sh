#!/usr/bin/env bash
# Project #1 — Generate all plots from CSV data
#
# This script generates all P1 plots from existing CSV files.
# Use this if you already have CSV data and just want to regenerate plots.
#
# Usage:
#   bash p1/scripts/generate_all_plots.sh
#
# Output:
#   PNG plots in p1/plots/

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

echo "Generating P1 plots..."
mkdir -p "${ROOT_DIR}/p1/plots"

# ===== Non-stride plots (vs N) =====
echo "  - SAXPY vs N..."
python3 "${ROOT_DIR}/p1/scripts/plot_p1.py" \
  --in "${ROOT_DIR}/p1/data/raw/p1_saxpy.csv" \
  --out "${ROOT_DIR}/p1/plots/saxpy_vs_n.png" \
  --xaxis n

echo "  - DOT vs N..."
python3 "${ROOT_DIR}/p1/scripts/plot_p1.py" \
  --in "${ROOT_DIR}/p1/data/raw/p1_dot.csv" \
  --out "${ROOT_DIR}/p1/plots/dot_vs_n.png" \
  --xaxis n

echo "  - MUL vs N..."
python3 "${ROOT_DIR}/p1/scripts/plot_p1.py" \
  --in "${ROOT_DIR}/p1/data/raw/p1_mul.csv" \
  --out "${ROOT_DIR}/p1/plots/mul_vs_n.png" \
  --xaxis n

echo "  - STENCIL vs N..."
python3 "${ROOT_DIR}/p1/scripts/plot_p1.py" \
  --in "${ROOT_DIR}/p1/data/raw/p1_stencil.csv" \
  --out "${ROOT_DIR}/p1/plots/stencil_vs_n.png" \
  --xaxis n

# ===== Stride plots (vs stride at N=2^20=1048576) =====
echo "  - SAXPY vs stride..."
python3 "${ROOT_DIR}/p1/scripts/plot_p1.py" \
  --in "${ROOT_DIR}/p1/data/raw/p1_saxpy_stride.csv" \
  --out "${ROOT_DIR}/p1/plots/saxpy_vs_stride.png" \
  --xaxis stride \
  --fixed_n 1048576

echo "  - DOT vs stride..."
python3 "${ROOT_DIR}/p1/scripts/plot_p1.py" \
  --in "${ROOT_DIR}/p1/data/raw/p1_dot_stride.csv" \
  --out "${ROOT_DIR}/p1/plots/dot_vs_stride.png" \
  --xaxis stride \
  --fixed_n 1048576

echo "  - MUL vs stride..."
python3 "${ROOT_DIR}/p1/scripts/plot_p1.py" \
  --in "${ROOT_DIR}/p1/data/raw/p1_mul_stride.csv" \
  --out "${ROOT_DIR}/p1/plots/mul_vs_stride.png" \
  --xaxis stride \
  --fixed_n 1048576

echo "  - STENCIL vs stride..."
python3 "${ROOT_DIR}/p1/scripts/plot_p1.py" \
  --in "${ROOT_DIR}/p1/data/raw/p1_stencil_stride.csv" \
  --out "${ROOT_DIR}/p1/plots/stencil_vs_stride.png" \
  --xaxis stride \
  --fixed_n 1048576

# ===== Alignment comparison plots =====
echo "  - SAXPY alignment..."
python3 "${ROOT_DIR}/p1/scripts/plot_p1.py" \
  --in "${ROOT_DIR}/p1/data/raw/p1_saxpy.csv" \
  --out "${ROOT_DIR}/p1/plots/saxpy_alignment.png" \
  --xaxis n \
  --include_misaligned

echo "  - DOT alignment..."
python3 "${ROOT_DIR}/p1/scripts/plot_p1.py" \
  --in "${ROOT_DIR}/p1/data/raw/p1_dot.csv" \
  --out "${ROOT_DIR}/p1/plots/dot_alignment.png" \
  --xaxis n \
  --include_misaligned

echo "  - MUL alignment..."
python3 "${ROOT_DIR}/p1/scripts/plot_p1.py" \
  --in "${ROOT_DIR}/p1/data/raw/p1_mul.csv" \
  --out "${ROOT_DIR}/p1/plots/mul_alignment.png" \
  --xaxis n \
  --include_misaligned

echo "  - STENCIL alignment..."
python3 "${ROOT_DIR}/p1/scripts/plot_p1.py" \
  --in "${ROOT_DIR}/p1/data/raw/p1_stencil.csv" \
  --out "${ROOT_DIR}/p1/plots/stencil_alignment.png" \
  --xaxis n \
  --include_misaligned

# ===== Roofline plot =====
echo "  - Roofline model..."
python3 "${ROOT_DIR}/p1/scripts/plot_roofline.py" \
  --data_dir "${ROOT_DIR}/p1/data/raw" \
  --out "${ROOT_DIR}/p1/plots/roofline.png"

echo
echo "✅ All plots generated in: ${ROOT_DIR}/p1/plots/"
echo "Total plots: 13 (4 vs_n, 4 vs_stride, 4 alignment, 1 roofline)"
echo "Done!"
