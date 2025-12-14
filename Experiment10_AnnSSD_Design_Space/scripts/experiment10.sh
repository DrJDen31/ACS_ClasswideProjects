#!/usr/bin/env bash
set -euo pipefail

# Experiment 10 driver: ANN-in-SSD design space exploration.
# Usage (from project root, inside WSL):
#   cd experiments/Experiment10_AnnSSD_Design_Space
#   ./scripts/experiment10.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
EXPERIMENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_DIR="$(cd "${EXPERIMENT_DIR}/../.." && pwd)"

CONFIG_FILE="${EXPERIMENT_DIR}/config/experiment10.conf"
if [[ -f "${CONFIG_FILE}" ]]; then
  # Strip potential CR characters (Windows line endings) into a temp file
  TMP_CONF="$(mktemp)"
  tr -d '\r' < "${CONFIG_FILE}" > "${TMP_CONF}"
  # shellcheck source=/dev/null
  source "${TMP_CONF}"
  rm -f "${TMP_CONF}"
fi

cd "${PROJECT_DIR}"

RAW_DIR="${EXPERIMENT_DIR}/results/raw"
mkdir -p "${RAW_DIR}"

NUM_BASE=${NUM_BASE:-20000}
NUM_QUERIES=${NUM_QUERIES:-2000}
DIM=${DIM:-128}
K=${K:-10}
SEED=${SEED:-42}
DATASET_NAME=${DATASET_NAME:-synthetic_gaussian}
ANN_HW_LEVEL=${ANN_HW_LEVEL:-L2}
ANN_MODE=${ANN_MODE:-cheated}
JSON_OUT_BASENAME=${JSON_OUT_BASENAME:-exp10}

read -r -a K_VALUES_ARR <<< "${K_VALUES:-128}"
read -r -a STEPS_VALUES_ARR <<< "${STEPS_VALUES:-0}"
read -r -a PORTAL_VALUES_ARR <<< "${PORTAL_VALUES:-1}"

for KPB in "${K_VALUES_ARR[@]}"; do
  for STEPS in "${STEPS_VALUES_ARR[@]}"; do
    for P in "${PORTAL_VALUES_ARR[@]}"; do
      local_suffix="_K-${KPB}_steps-${STEPS}_P-${P}"
      json_out="${RAW_DIR}/${JSON_OUT_BASENAME}${local_suffix}.json"
      echo "[Experiment10] K=${KPB}, max_steps=${STEPS}, portal_degree=${P} -> ${json_out}" >&2

      ./bin/benchmark_recall \
        --mode ann_ssd \
        --num-base "${NUM_BASE}" \
        --num-queries "${NUM_QUERIES}" \
        --dim "${DIM}" \
        --k "${K}" \
        --seed "${SEED}" \
        --dataset-name "${DATASET_NAME}" \
        --ann-ssd-mode "${ANN_MODE}" \
        --ann-hw-level "${ANN_HW_LEVEL}" \
        --ann-vectors-per-block "${KPB}" \
        --ann-max-steps "${STEPS}" \
        --ann-portal-degree "${P}" \
        --json-out "${json_out}"
    done
  done
done
