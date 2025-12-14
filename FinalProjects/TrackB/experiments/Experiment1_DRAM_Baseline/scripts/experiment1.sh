#!/usr/bin/env bash
set -euo pipefail

# Experiment 1 driver: DRAM baseline (and variants) for benchmark_recall.
# All tunable parameters live in ../config/experiment1.conf

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
EXPERIMENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_DIR="$(cd "${EXPERIMENT_DIR}/../.." && pwd)"

CONFIG_FILE="${EXPERIMENT_DIR}/config/experiment1.conf"
if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "Config file not found: ${CONFIG_FILE}" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "${CONFIG_FILE}"

cd "${PROJECT_DIR}"

mkdir -p "${EXPERIMENT_DIR}/results/raw"

# Discover sweep dimensions from optional SWEEP_* variables defined in the config.
PARAMS=()
declare -A SWEEP_VALUES

while IFS= read -r var; do
  value="${!var-}"
  if [[ -z "${value}" ]]; then
    continue
  fi
  base="${var#SWEEP_}"
  PARAMS+=("${base}")
  SWEEP_VALUES["${base}"]="${value}"
done < <(compgen -A variable | grep '^SWEEP_')

num_params=${#PARAMS[@]}

run_one() {
  local suffix=""
  for base in "${PARAMS[@]}"; do
    local current="${!base-}"
    if [[ -n "${current}" ]]; then
      local pretty="${current}"
      # If the sweep value is purely numeric, zero-pad it so filenames
      # sort correctly (e.g., 16 -> 0016). The underlying parameter
      # value passed to the binary remains unpadded.
      if [[ "${current}" =~ ^[0-9]+$ ]]; then
        printf -v pretty "%04d" "${current}"
      fi
      suffix+="_${base}-${pretty}"
    fi
  done

  local json_out="${EXPERIMENT_DIR}/results/raw/${JSON_OUT_BASENAME}${suffix}.json"

  ARGS=(
    --mode "${MODE}"
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

  if [[ "${MODE}" == "tiered" ]]; then
    ARGS+=( --cache-capacity "${CACHE_CAPACITY}" )
  fi

  if [[ -n "${DATASET_PATH}" ]]; then
    ARGS+=( --dataset-path "${DATASET_PATH}" --dataset-name "${DATASET_NAME}" )
  fi

  if [[ -n "${QUERY_PATH}" && -n "${GROUNDTRUTH_PATH}" ]]; then
    ARGS+=( --query-path "${QUERY_PATH}" --groundtruth-path "${GROUNDTRUTH_PATH}" )
  fi

  ./bin/benchmark_recall "${ARGS[@]}"
}

# If no sweeps are defined, run a single experiment using the base config.
if (( num_params == 0 )); then
  run_one
  exit 0
fi

# Build value lists and an index vector for the Cartesian product of all sweeps.
declare -a IDX
declare -a LENS

for base in "${PARAMS[@]}"; do
  value="${SWEEP_VALUES[${base}]}"
  read -r -a arr <<< "${value}"
  eval "VALUES_${base}=(\"\${arr[@]}\")"
  LENS+=("${#arr[@]}")
  IDX+=(0)
done

while :; do
  # Set current parameter values for this combination.
  for ((i = 0; i < num_params; ++i)); do
    base="${PARAMS[i]}"
    idx="${IDX[i]}"
    eval "vals=(\"\${VALUES_${base}[@]}\")"
    val="${vals[${idx}]}"
    printf -v "${base}" '%s' "${val}"
  done

  run_one

  # Increment mixed-radix counter over sweep dimensions.
  inc=$(( num_params - 1 ))
  while (( inc >= 0 )); do
    idx="${IDX[inc]}"
    len="${LENS[inc]}"
    if (( idx + 1 < len )); then
      IDX[inc]=$(( idx + 1 ))
      for ((j = inc + 1; j < num_params; ++j)); do
        IDX[j]=0
      done
      break
    else
      (( inc-- ))
    fi
  done

  if (( inc < 0 )); then
    break
  fi
done

