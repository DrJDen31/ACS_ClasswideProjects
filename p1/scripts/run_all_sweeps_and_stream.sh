#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

# Non-stride sweeps (dtype + aligned/misaligned)
bash "${ROOT_DIR}/scripts/p1/run_all_sweeps.sh"

# Stride + dtype sweeps (fixed N loops inside scripts)
bash "${ROOT_DIR}/scripts/p1/run_all_stride_dtype_sweeps.sh"

# STREAM
bash "${ROOT_DIR}/scripts/p1/run_stream.sh"

echo "All sweeps + STREAM complete. See data/raw/ for CSVs and stream.txt."
