#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
BUILD_DIR="${ROOT_DIR}/build"
OUT_CSV="${ROOT_DIR}/data/raw/p1_saxpy_stride.csv"
  mkdir -p "${BUILD_DIR}" "${ROOT_DIR}/data/raw"
if [[ ! -f "${BUILD_DIR}/build.ninja" && ! -f "${BUILD_DIR}/Makefile" ]]; then
  cmake -S "${ROOT_DIR}" -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE=Release
fi
cmake --build "${BUILD_DIR}" -j

  sizes=(); for p in $(seq 12 26); do sizes+=( $((1<<p)) ); done
  variants=("saxpy_scalar" "saxpy_auto" "saxpy_avx2")
  strides=(1 2 4 8 16 32 64)
  dtypes=("f32" "f64")
  reps=7

# Optional randomization to mitigate drift
  if [[ "${RANDOMIZE:-0}" == "1" ]]; then
    if command -v shuf >/dev/null 2>&1; then
      sizes=($(printf "%s\n" "${sizes[@]}" | shuf))
      variants=($(printf "%s\n" "${variants[@]}" | shuf))
      strides=($(printf "%s\n" "${strides[@]}" | shuf))
      dtypes=($(printf "%s\n" "${dtypes[@]}" | shuf))
    else
      echo "[warn] shuf not found; skipping randomization" >&2
    fi
  fi

  # Fresh CSV with header (includes stride and dtype)
  rm -f "${OUT_CSV}"
  echo "variant,n,reps,misaligned,median_ms,best_ms,gflops,max_abs_err,stride,dtype" >"${OUT_CSV}"
for dt in "${dtypes[@]}"; do
  for s in "${strides[@]}"; do
    for n in "${sizes[@]}"; do
      for v in "${variants[@]}"; do
        bin="${BUILD_DIR}/bin/${v}"
        [[ -x "${bin}" ]] || { echo "Missing binary: ${bin}" >&2; exit 2; }
        # aligned
        line=$("${bin}" --size "${n}" --reps "${reps}" --stride "${s}" --dtype "${dt}" | tail -n +2)
        rest=$(printf "%s" "${line}" | cut -d, -f2-)
        echo "${v},${rest},${s},${dt}" >>"${OUT_CSV}"
        # misaligned
        line=$("${bin}" --size "${n}" --reps "${reps}" --stride "${s}" --dtype "${dt}" --misaligned | tail -n +2)
        rest=$(printf "%s" "${line}" | cut -d, -f2-)
        echo "${v},${rest},${s},${dt}" >>"${OUT_CSV}"
      done
    done
  done
done

echo "Wrote: ${OUT_CSV}"