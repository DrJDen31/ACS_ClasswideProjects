#!/usr/bin/env bash
# Project #1 — Vectorization reports (WSL/Linux)
#
# Purpose:
# - Configure a separate build directory with compiler flags to emit
#   vectorization reports, build all P1 targets, and save the build
#   output to data/raw/p1_vectorize_build.log
#
# Detection:
# - Detects compiler via CMakeCache.txt (CMAKE_CXX_COMPILER_ID) and applies:
#   * Clang: -Rpass=loop-vectorize -Rpass-missed=loop-vectorize -Rpass-analysis=loop-vectorize
#   * GCC:   -fopt-info-vec-optimized -fopt-info-vec-missed
#
# Usage:
#   bash scripts/p1/vectorization_reports.sh
#
# Output:
#   data/raw/p1_vectorize_build.log

set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
BUILD_VEC_DIR="${ROOT_DIR}/build_vec"
LOG_DIR="${ROOT_DIR}/data/raw"
LOG_FILE="${LOG_DIR}/p1_vectorize_build.log"
mkdir -p "${BUILD_VEC_DIR}" "${LOG_DIR}"

# First configure (to get compiler ID)
if [[ ! -f "${BUILD_VEC_DIR}/CMakeCache.txt" ]]; then
  cmake -S "${ROOT_DIR}" -B "${BUILD_VEC_DIR}" -DCMAKE_BUILD_TYPE=Release
fi

# Detect compiler ID
COMP_ID=$(grep -E "^CMAKE_CXX_COMPILER_ID" "${BUILD_VEC_DIR}/CMakeCache.txt" | sed -E 's/.*=//')
FLAGS=""
case "${COMP_ID}" in
  Clang)
    FLAGS="-Rpass=loop-vectorize -Rpass-missed=loop-vectorize -Rpass-analysis=loop-vectorize"
    ;;
  GNU)
    FLAGS="-fopt-info-vec-optimized -fopt-info-vec-missed"
    ;;
  *)
    echo "Unknown compiler ID: ${COMP_ID}. Proceeding without special flags." >&2
    ;;
 esac

# Re-configure with flags if known
if [[ -n "${FLAGS}" ]]; then
  cmake -S "${ROOT_DIR}" -B "${BUILD_VEC_DIR}" -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_CXX_FLAGS="${FLAGS}"
fi

# Build and capture output
{
  echo "[Vectorization build] Compiler: ${COMP_ID}"
  echo "[Vectorization build] Flags: ${FLAGS}"
  cmake --build "${BUILD_VEC_DIR}" -j
} >"${LOG_FILE}" 2>&1 || true

echo "Wrote: ${LOG_FILE}"
