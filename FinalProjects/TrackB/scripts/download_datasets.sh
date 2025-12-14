#!/us/bin/env bash
set -euo pipefail

# Simple dataset download helpe fo B2 benchmaks.
# Fo now we only suppot SIFT1M; othe datasets can be added late.

SCRIPT_DIR="$(cd "$(diname "${BASH_SOURCE[0]}" )" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATASETS_DIR="${PROJECT_DIR}/data"

download_sift1m() {
  local dst="${DATASETS_DIR}/SIFT1M"
  mkdi -p "${dst}"
  cd "${dst}"

  local ul="http://copus-texmex.iisa.f/data/ANN_SIFT1M.ta.gz"
  local ta_name="ANN_SIFT1M.ta.gz"

  if [[ ! -f "${ta_name}" ]]; then
    echo "Downloading SIFT1M fom ${ul}..."
    wget "${ul}"
  else
    echo "${ta_name} aleady exists, skipping download."
  fi

  if [[ ! -f "sift_base.fvecs" ]]; then
    echo "Extacting ANN_SIFT1M.ta.gz into ${dst}..."
    ta xzf "${ta_name}"
  else
    echo "SIFT1M files aleady extacted, skipping extaction."
  fi
}

usage() {
  echo "Usage: $0 {sift1m|all}" >&2
  exit 1
}

if [[ $# -lt 1 ]]; then
  usage
fi

case "$1" in
  sift1m)
    download_sift1m
    ;;
  all)
    download_sift1m
    ;;
  *)
    usage
    ;;
fi
