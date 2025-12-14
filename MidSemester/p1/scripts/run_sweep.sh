#!/usr/bin/env bash
# Project #1 — SAXPY sweep runner (WSL/Linux)
#
# Purpose:
# - Build the project (Release) and run SAXPY across sizes 2^12..2^26
# - Execute three variants: scalar, auto (march=native), avx2 (mavx2+mfma)
# - For each size and variant, run aligned and misaligned cases
# - Append CSV rows to data/raw/p1_saxpy.csv
#
# Usage:
#   bash scripts/p1/run_sweep.sh
#
# Notes:
# - Assumes CMake, g++/clang++, and a Linux/WSL environment.
# - CSV columns: variant,n,reps,misaligned, median_ms,best_ms,gflops,max_abs_err
# - Repetitions are set in this script via `reps` variable.

set -euo pipefail

# Build (Release) if needed
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
BUILD_DIR="${ROOT_DIR}/build"
OUT_CSV="${ROOT_DIR}/data/raw/p1_saxpy.csv"
mkdir -p "${BUILD_DIR}" "${ROOT_DIR}/data/raw"

if [[ ! -f "${BUILD_DIR}/build.ninja" && ! -f "${BUILD_DIR}/Makefile" ]]; then
  cmake -S "${ROOT_DIR}" -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE=Release
fi
cmake --build "${BUILD_DIR}" -j

# Sizes: 2^12 .. 2^26
sizes=()
for p in $(seq 12 26); do sizes+=( $((1<<p)) ); done

variants=("saxpy_scalar" "saxpy_auto" "saxpy_avx2")
reps=7

if [[ ! -f "${OUT_CSV}" ]]; then
  echo "variant,n,reps,misaligned,median_ms,best_ms,gflops,max_abs_err" >"${OUT_CSV}"
fi

for n in "${sizes[@]}"; do
  for v in "${variants[@]}"; do
    bin="${BUILD_DIR}/bin/${v}"
    if [[ ! -x "${bin}" ]]; then
      echo "Missing binary: ${bin}" >&2; exit 2
    fi
    # aligned
    "${bin}" --size "${n}" --reps "${reps}" | tail -n +2 >>"${OUT_CSV}"
    # misaligned
    "${bin}" --size "${n}" --reps "${reps}" --misaligned | tail -n +2 >>"${OUT_CSV}"
  done
done

echo "Wrote: ${OUT_CSV}"
