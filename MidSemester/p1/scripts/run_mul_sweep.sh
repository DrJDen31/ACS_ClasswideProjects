#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
BUILD_DIR="${ROOT_DIR}/build"
OUT_CSV="${ROOT_DIR}/data/raw/p1_mul.csv"
mkdir -p "${BUILD_DIR}" "${ROOT_DIR}/data/raw"

# Skip rebuild to reuse existing binaries

sizes=(); for p in $(seq 12 26); do sizes+=( $((1<<p)) ); done
variants=("mul_scalar" "mul_auto" "mul_avx2")
dtypes=("f32" "f64")
reps=7

# Optional randomization to mitigate drift
if [[ "${RANDOMIZE:-0}" == "1" ]]; then
  if command -v shuf >/dev/null 2>&1; then
    sizes=($(printf "%s\n" "${sizes[@]}" | shuf))
    variants=($(printf "%s\n" "${variants[@]}" | shuf))
    dtypes=($(printf "%s\n" "${dtypes[@]}" | shuf))
  else
    echo "[warn] shuf not found; skipping randomization" >&2
  fi
fi

# Fresh CSV with header (includes dtype)
rm -f "${OUT_CSV}"
echo "variant,n,reps,misaligned,median_ms,best_ms,gflops,max_abs_err,dtype" >"${OUT_CSV}"

for n in "${sizes[@]}"; do
  for v in "${variants[@]}"; do
    bin="${BUILD_DIR}/bin/${v}"
    [[ -x "${bin}" ]] || { echo "Missing binary: ${bin}" >&2; exit 2; }
    for dt in "${dtypes[@]}"; do
      # aligned
      line=$("${bin}" --size "${n}" --reps "${reps}" --dtype "${dt}" | tail -n +2)
      rest=$(printf "%s" "${line}" | cut -d, -f2-)
      echo "${v},${rest},${dt}" >>"${OUT_CSV}"
      # misaligned
      line=$("${bin}" --size "${n}" --reps "${reps}" --dtype "${dt}" --misaligned | tail -n +2)
      rest=$(printf "%s" "${line}" | cut -d, -f2-)
      echo "${v},${rest},${dt}" >>"${OUT_CSV}"
    done
  done
done

echo "Wrote: ${OUT_CSV}"
