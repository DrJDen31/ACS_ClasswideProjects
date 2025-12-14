#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
EXPERIMENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_DIR="$(cd "${EXPERIMENT_DIR}/../.." && pwd)"

cd "${PROJECT_DIR}"

python3 "${EXPERIMENT_DIR}/scripts/run_experiment8.py"
