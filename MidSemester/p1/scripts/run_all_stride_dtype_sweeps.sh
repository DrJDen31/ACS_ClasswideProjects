#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
bash "${ROOT_DIR}/run_saxpy_stride_sweep.sh"
bash "${ROOT_DIR}/run_dot_stride_sweep.sh"
bash "${ROOT_DIR}/run_mul_stride_sweep.sh"
bash "${ROOT_DIR}/run_stencil_stride_sweep.sh"