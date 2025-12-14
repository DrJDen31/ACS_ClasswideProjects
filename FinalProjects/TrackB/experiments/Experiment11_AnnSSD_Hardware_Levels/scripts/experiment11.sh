#!/usr/bin/env bash
set -euo pipefail

# Experiment 11 driver: ANN-in-SSD hardware levels (L0–L3),
# faithful vs cheated, across several num_base values.
# Run this from within WSL, e.g.:
#   cd experiments/Experiment11_AnnSSD_Hardware_Levels
#   ./scripts/experiment11.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
EXPERIMENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_DIR="$(cd "${EXPERIMENT_DIR}/../.." && pwd)"

cd "${PROJECT_DIR}"

RESULT_DIR="${EXPERIMENT_DIR}/results/raw"
mkdir -p "${RESULT_DIR}"

NUM_BASES=(5000 20000 80000)
LEVELS=(L0 L1 L2 L3)
SIM_MODES=(faithful cheated)

NUM_QUERIES=${NUM_QUERIES:-2000}
DIM=${DIM:-128}
K=${K:-10}
SEED=${SEED:-42}
DATASET_NAME=${DATASET_NAME:-synthetic_gaussian}

# Reference configuration used to define a target "fraction of blocks" to
# visit. We keep this fraction roughly constant across different num_base
# values so that recall stays approximately fixed while query cost scales
# with dataset size.
ANN_VECTORS_PER_BLOCK=128
REF_NUM_BASE=20000
REF_MAX_STEPS=20
REF_BLOCKS=$(( (REF_NUM_BASE + ANN_VECTORS_PER_BLOCK - 1) / ANN_VECTORS_PER_BLOCK ))

for nb in "${NUM_BASES[@]}"; do
  # Derive max_steps so that the fraction of blocks visited is roughly
  # constant across num_base values. This keeps recall approximately
  # fixed while letting latency/throughput scale with dataset size.
  num_blocks=$(( (nb + ANN_VECTORS_PER_BLOCK - 1) / ANN_VECTORS_PER_BLOCK ))
  max_steps=$(( num_blocks * REF_MAX_STEPS / REF_BLOCKS ))
  if [[ "${max_steps}" -lt 1 ]]; then
    max_steps=1
  fi

  for level in "${LEVELS[@]}"; do
    for mode in "${SIM_MODES[@]}"; do
      out="${RESULT_DIR}/annssd_nb-${nb}_level-${level}_mode-${mode}.json"
      echo "[Experiment11] num_base=${nb}, level=${level}, mode=${mode}, max_steps=${max_steps} -> ${out}" >&2

      ./bin/benchmark_recall \
        --mode ann_ssd \
        --num-base "${nb}" \
        --num-queries "${NUM_QUERIES}" \
        --dim "${DIM}" \
        --k "${K}" \
        --seed "${SEED}" \
        --dataset-name "${DATASET_NAME}" \
        --ann-ssd-mode "${mode}" \
        --ann-hw-level "${level}" \
        --ann-vectors-per-block "${ANN_VECTORS_PER_BLOCK}" \
        --ann-max-steps "${max_steps}" \
        --ann-portal-degree 2 \
        --json-out "${out}"
    done
  done
done
