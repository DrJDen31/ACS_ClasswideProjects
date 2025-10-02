#!/usr/bin/env bash
# Project #1 — Orchestrator to run all sweeps (WSL/Linux)
#
# This script builds the project (Release) and runs all available P1 sweeps:
# - SAXPY:    scripts/p1/run_sweep.sh           -> data/raw/p1_saxpy.csv
# - DOT:      scripts/p1/run_dot_sweep.sh       -> data/raw/p1_dot.csv
# - MUL:      scripts/p1/run_mul_sweep.sh       -> data/raw/p1_mul.csv
# - STENCIL:  scripts/p1/run_stencil_sweep.sh   -> data/raw/p1_stencil.csv
#
# Usage:
#   bash scripts/p1/run_all_sweeps.sh
#
# Notes:
# - Assumes CMake, g++/clang++, and a Linux/WSL environment.
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
BUILD_DIR="${ROOT_DIR}/build"

# Skip rebuild (assumes binaries exist)

# Run individual sweeps
bash "${ROOT_DIR}/scripts/p1/run_saxpy_sweep.sh"
bash "${ROOT_DIR}/scripts/p1/run_dot_sweep.sh"
bash "${ROOT_DIR}/scripts/p1/run_mul_sweep.sh"
bash "${ROOT_DIR}/scripts/p1/run_stencil_sweep.sh"

echo "All sweeps completed. See data/raw/ for CSV outputs."
