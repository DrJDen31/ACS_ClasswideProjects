#!/usr/bin/env bash
# Project #1 — DOT (reduction) sweep runner (WSL/Linux)
#
# Purpose:
# - Build the project (Release) and run DOT across sizes 2^12..2^26
# - Execute three variants: dot_scalar, dot_auto (march=native), dot_avx2 (mavx2+mfma)
# - For each size and variant, run aligned and misaligned cases
# - Append CSV rows to data/raw/p1_dot.csv
#
# Usage:
#   bash scripts/p1/run_dot_sweep.sh
#
# Notes:
# - Assumes CMake, g++/clang++, and a Linux/WSL environment.
# - CSV columns: variant,n,reps,misaligned,median_ms,best_ms,gflops,max_abs_err
# - Repetitions are set in this script via `reps` variable.
set -euo pipefail

# Build (Release) if needed
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
BUILD_DIR="${ROOT_DIR}/build"
OUT_CSV="${ROOT_DIR}/data/raw/p1_dot.csv"
mkdir -p "${BUILD_DIR}" "${ROOT_DIR}/data/raw"

if [[ ! -f "${BUILD_DIR}/build.ninja" && ! -f "${BUILD_DIR}/Makefile" ]]; then
  cmake -S "${ROOT_DIR}" -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE=Release
fi
cmake --build "${BUILD_DIR}" -j
# Sizes: 2^12 .. 2^26
sizes=()
for p in $(seq 12 26); do sizes+=( $((1<<p)) ); done

variants=("dot_scalar" "dot_auto" "dot_avx2")
dtypes=("f32" "f64")
reps=7

# Optional randomization to mitigate drift
if [[ "${RANDOMIZE:-0}" == "1" ]]; then
  if command -v shuf >/dev/null 2>&1; then
    sizes=($(printf "%s\n" "${sizes[@]}" | shuf))
    variants=($(printf "%s\n" "${variants[@]}" | shuf))
    dtypes=($(printf "%s\n" "${dtypes[@]}" | shuf))
  else
    echo "[warn] shuf not found; skipping randomization" >&2
  fi
fi

rm -f "${OUT_CSV}"
echo "variant,n,reps,misaligned,median_ms,best_ms,gflops,max_abs_err,dtype" >"${OUT_CSV}"

for n in "${sizes[@]}"; do
  for v in "${variants[@]}"; do
    bin="${BUILD_DIR}/bin/${v}"
    if [[ ! -x "${bin}" ]]; then
      echo "Missing binary: ${bin}" >&2; exit 2
    fi
    for dt in "${dtypes[@]}"; do
      # aligned
      line=$("${bin}" --size "${n}" --reps "${reps}" --dtype "${dt}" | tail -n +2)
      rest=$(printf "%s" "${line}" | cut -d, -f2-)
      echo "${v},${rest},${dt}" >>"${OUT_CSV}"
      # misaligned
      line=$("${bin}" --size "${n}" --reps "${reps}" --dtype "${dt}" --misaligned | tail -n +2)
      rest=$(printf "%s" "${line}" | cut -d, -f2-)
      echo "${v},${rest},${dt}" >>"${OUT_CSV}"
    done
  done
done

echo "Wrote: ${OUT_CSV}"