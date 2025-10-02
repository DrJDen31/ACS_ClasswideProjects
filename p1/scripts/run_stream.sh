#!/usr/bin/env bash
# Download, build, and run STREAM single-threaded; save result to data/raw/stream.txt
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
STREAM_DIR="${ROOT_DIR}/third_party/stream"
OUT_TXT="${ROOT_DIR}/data/raw/stream.txt"

mkdir -p "${STREAM_DIR}" "${ROOT_DIR}/data/raw"
cd "${STREAM_DIR}"

# Fetch stream.c
if [[ ! -f stream.c ]]; then
  if command -v wget >/dev/null 2>&1; then
    wget -qO stream.c https://www.cs.virginia.edu/stream/FTP/Code/stream.c
  elif command -v curl >/dev/null 2>&1; then
    curl -fsSL -o stream.c https://www.cs.virginia.edu/stream/FTP/Code/stream.c
  else
    echo "Please install wget or curl (e.g., sudo apt-get install wget)" >&2
    exit 1
  fi
fi

# Build with OpenMP, optimize, and use a large array with a few iterations
: "${STREAM_ARRAY_SIZE:=80000000}"
: "${NTIMES:=10}"

echo "[STREAM] Building..."
gcc -O3 -fopenmp -march=native -mtune=native \
    -DSTREAM_ARRAY_SIZE=${STREAM_ARRAY_SIZE} -DNTIMES=${NTIMES} \
    stream.c -o stream_exe

echo "[STREAM] Running single-threaded..."
export OMP_NUM_THREADS=1
./stream_exe | tee "${OUT_TXT}"

echo "[STREAM] Wrote: ${OUT_TXT}"
