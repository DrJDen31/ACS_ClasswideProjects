#!/usr/bin/env bash
set -euo pipefail

# Experiment 9 driver: DRAM vs Tiered vs ANN-SSD on a common dataset.
# Usage (from project root, inside WSL):
#   cd experiments/Experiment9_AnnSSD_vs_Tiered_vs_DRAM
#   ./scripts/experiment9.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
EXPERIMENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_DIR="$(cd "${EXPERIMENT_DIR}/../.." && pwd)"

CONFIG_FILE="${EXPERIMENT_DIR}/config/experiment9.conf"
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
EF_SEARCH=${EF_SEARCH:-100}
M=${M:-16}
EF_CONSTRUCTION=${EF_CONSTRUCTION:-200}
SEED=${SEED:-42}
CACHE_CAPACITY=${CACHE_CAPACITY:-10000}
DATASET_PATH=${DATASET_PATH:-}
DATASET_NAME=${DATASET_NAME:-synthetic_gaussian}
QUERY_PATH=${QUERY_PATH:-}
GROUNDTRUTH_PATH=${GROUNDTRUTH_PATH:-}
JSON_OUT_BASENAME=${JSON_OUT_BASENAME:-exp9}

# ANN-in-SSD tuning knobs (mirrors Experiment 12 defaults).
ANN_VECTORS_PER_BLOCK=${ANN_VECTORS_PER_BLOCK:-128}
ANN_PORTAL_DEGREE=${ANN_PORTAL_DEGREE:-2}

run_dram() {
  local suffix="$1"
  local json_out="${RAW_DIR}/${JSON_OUT_BASENAME}_mode-dram${suffix}.json"
  echo "[Experiment9] DRAM -> ${json_out}" >&2

  ARGS=(
    --mode dram
    --num-base "${NUM_BASE}"
    --num-queries "${NUM_QUERIES}"
    --dim "${DIM}"
    --k "${K}"
    --ef-search "${EF_SEARCH}"
    --M "${M}"
    --ef-construction "${EF_CONSTRUCTION}"
    --seed "${SEED}"
    --json-out "${json_out}"
  )

  if [[ -n "${DATASET_PATH}" ]]; then
    ARGS+=( --dataset-path "${DATASET_PATH}" --dataset-name "${DATASET_NAME}" )
  fi
  if [[ -n "${QUERY_PATH}" && -n "${GROUNDTRUTH_PATH}" ]]; then
    ARGS+=( --query-path "${QUERY_PATH}" --groundtruth-path "${GROUNDTRUTH_PATH}" )
  fi

  ./bin/benchmark_recall "${ARGS[@]}"
}

run_tiered() {
  local suffix="$1"
  local json_out="${RAW_DIR}/${JSON_OUT_BASENAME}_mode-tiered${suffix}.json"
  echo "[Experiment9] Tiered -> ${json_out}" >&2

  ARGS=(
    --mode tiered
    --num-base "${NUM_BASE}"
    --num-queries "${NUM_QUERIES}"
    --dim "${DIM}"
    --k "${K}"
    --ef-search "${EF_SEARCH}"
    --M "${M}"
    --ef-construction "${EF_CONSTRUCTION}"
    --seed "${SEED}"
    --cache-capacity "${CACHE_CAPACITY}"
    --json-out "${json_out}"
  )

  if [[ -n "${DATASET_PATH}" ]]; then
    ARGS+=( --dataset-path "${DATASET_PATH}" --dataset-name "${DATASET_NAME}" )
  fi
  if [[ -n "${QUERY_PATH}" && -n "${GROUNDTRUTH_PATH}" ]]; then
    ARGS+=( --query-path "${QUERY_PATH}" --groundtruth-path "${GROUNDTRUTH_PATH}" )
  fi

  ./bin/benchmark_recall "${ARGS[@]}"
}

run_annssd_level() {
  local level="$1"       # L0/L2/L3
  local max_steps="$2"   # 0 for full scan, >0 for approximate
  local step_suffix="$3" # e.g., "" or "_steps78"
  local suffix="$4"      # dataset suffix (e.g., _dataset-synth)

  local json_out="${RAW_DIR}/${JSON_OUT_BASENAME}_mode-annssd_level-${level}${step_suffix}${suffix}.json"
  echo "[Experiment9] ANN-SSD level=${level}, max_steps=${max_steps} -> ${json_out}" >&2

  ARGS=(
    --mode ann_ssd
    --num-base "${NUM_BASE}"
    --num-queries "${NUM_QUERIES}"
    --dim "${DIM}"
    --k "${K}"
    --seed "${SEED}"
    --dataset-name "${DATASET_NAME}"
    --ann-ssd-mode cheated
    --ann-hw-level "${level}"
    --ann-vectors-per-block "${ANN_VECTORS_PER_BLOCK}"
    --ann-max-steps "${max_steps}"
    --ann-portal-degree "${ANN_PORTAL_DEGREE}"
    --json-out "${json_out}"
  )

  if [[ -n "${DATASET_PATH}" ]]; then
    ARGS+=( --dataset-path "${DATASET_PATH}" --dataset-name "${DATASET_NAME}" )
  fi
  if [[ -n "${QUERY_PATH}" && -n "${GROUNDTRUTH_PATH}" ]]; then
    ARGS+=( --query-path "${QUERY_PATH}" --groundtruth-path "${GROUNDTRUTH_PATH}" )
  fi

  ./bin/benchmark_recall "${ARGS[@]}"
}

# For now we treat whatever CONFIG chooses (synthetic vs SIFT) as the single
# dataset for this experiment. If DATASET_PATH is empty we are on synthetic.
SUFFIX=""
if [[ -z "${DATASET_PATH}" ]]; then
  SUFFIX="_dataset-synth"
else
  SUFFIX="_dataset-real"
fi

run_dram "${SUFFIX}"
if [[ "${ENABLE_TIERED:-1}" == "1" ]]; then
  run_tiered "${SUFFIX}"
fi

# Derive a mid-steps and high-steps configuration as simple fractions of the
# total number of blocks. This mirrors the approach used in
# Experiment12_Unified_Comparison.
num_blocks=$(( (NUM_BASE + ANN_VECTORS_PER_BLOCK - 1) / ANN_VECTORS_PER_BLOCK ))
mid_steps=$(( num_blocks / 2 ))
if [[ "${mid_steps}" -lt 1 ]]; then
  mid_steps=1
fi
hi_steps=$(( num_blocks * 95 / 100 ))
if [[ "${hi_steps}" -lt 1 ]]; then
  hi_steps=1
fi

for level in L0 L2 L3; do
  # Full-scan / high-recall reference (max_steps=0)
  run_annssd_level "${level}" "0" "" "${SUFFIX}"
  # Mid-steps configuration (~0.5 * num_blocks)
  run_annssd_level "${level}" "${mid_steps}" "_steps${mid_steps}" "${SUFFIX}"
  # High-steps configuration (~0.95 * num_blocks)
  run_annssd_level "${level}" "${hi_steps}" "_steps${hi_steps}" "${SUFFIX}"
done
