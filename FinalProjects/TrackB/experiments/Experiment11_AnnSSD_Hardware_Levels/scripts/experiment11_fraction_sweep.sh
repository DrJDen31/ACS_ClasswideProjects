#!/usr/bin/env bash
set -euo pipefail

# Fraction-of-blocks sweep for ANN-in-SSD L3
# Sweeps num_base and, for each, sweeps fractions of blocks visited via max_steps.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
BIN="${PROJECT_ROOT}/bin/benchmark_recall"
OUT_DIR="${PROJECT_ROOT}/experiments/Experiment11_AnnSSD_Hardware_Levels/results/fraction_sweep"
mkdir -p "${OUT_DIR}"

DATASET_NAME="synthetic_gaussian"
DIM=128
K=10
NUM_QUERIES=50
SEED=42

HW_LEVEL="L3"
VECTORS_PER_BLOCK=128
PORTAL_DEGREE=8
ANN_SSD_MODE="cheated"
PLACEMENT_MODE="locality_aware"
CODE_TYPE="micro_index"

# Seven num_base points, roughly log-spaced
NUM_BASES=(20000 50000 100000 200000 400000 700000 1000000)

# Fractions of blocks (in percent) to visit via max_steps
FRACTIONS=(10 20 30 40 60 80)

for NB in "${NUM_BASES[@]}"; do
  # Number of blocks (ceil division)
  B=$(( (NB + VECTORS_PER_BLOCK - 1) / VECTORS_PER_BLOCK ))

  for F in "${FRACTIONS[@]}"; do
    MAX_STEPS=$(( B * F / 100 ))
    if [ "${MAX_STEPS}" -lt 1 ]; then
      MAX_STEPS=1
    fi

    OUT="${OUT_DIR}/annssd_nb-${NB}_L3_frac-${F}_ms-${MAX_STEPS}.json"

    echo "[fraction_sweep] NB=${NB}, frac=${F}%, blocks=${B}, max_steps=${MAX_STEPS} -> ${OUT}"

    "${BIN}" \
      --mode ann_ssd \
      --num-base "${NB}" \
      --num-queries "${NUM_QUERIES}" \
      --dim "${DIM}" \
      --k "${K}" \
      --seed "${SEED}" \
      --dataset-name "${DATASET_NAME}" \
      --ann-ssd-mode "${ANN_SSD_MODE}" \
      --ann-hw-level "${HW_LEVEL}" \
      --ann-vectors-per-block "${VECTORS_PER_BLOCK}" \
      --ann-portal-degree "${PORTAL_DEGREE}" \
      --ann-max-steps "${MAX_STEPS}" \
      --placement-mode "${PLACEMENT_MODE}" \
      --code-type "${CODE_TYPE}" \
      --json-out "${OUT}"
  done
done
