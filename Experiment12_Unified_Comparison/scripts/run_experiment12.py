#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


def _run(cmd: List[str], cwd: Path) -> None:
    print("\n[run_experiment12] exec:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if proc.returncode != 0:
        if proc.stdout:
            sys.stderr.write(proc.stdout)
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)
    if proc.stdout:
        sys.stdout.write(proc.stdout)


def _read_fvecs(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if not data:
        raise ValueError(f"Empty fvecs file: {path}")
    dim = np.frombuffer(data, dtype=np.int32, count=1)[0]
    if dim <= 0:
        raise ValueError(f"Invalid dim {dim} in fvecs file {path}")
    record_size = 4 + int(dim) * 4
    if len(data) % record_size != 0:
        raise ValueError(
            f"File size {len(data)} not divisible by record size {record_size} for dim {dim}"
        )
    n = len(data) // record_size
    arr = np.frombuffer(data, dtype=np.int32).reshape(n, 1 + int(dim))
    vecs = arr[:, 1:].view(np.float32)
    return vecs.copy()


def _read_ivecs(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if not data:
        raise ValueError(f"Empty ivecs file: {path}")
    dim = np.frombuffer(data, dtype=np.int32, count=1)[0]
    if dim <= 0:
        raise ValueError(f"Invalid dim {dim} in ivecs file {path}")
    record_size = 4 + int(dim) * 4
    if len(data) % record_size != 0:
        raise ValueError(
            f"File size {len(data)} not divisible by record size {record_size} for dim {dim}"
        )
    n = len(data) // record_size
    arr = np.frombuffer(data, dtype=np.int32).reshape(n, 1 + int(dim))
    ids = arr[:, 1:]
    return ids.copy()


def _compute_gt_knn_l2_chunked(
    base: np.ndarray, queries: np.ndarray, k: int, chunk_q: int = 200
) -> np.ndarray:
    nq = queries.shape[0]
    if nq == 0:
        return np.empty((0, k), dtype=np.int32)

    gt = np.empty((nq, k), dtype=np.int32)
    b_norms = np.sum(base ** 2, axis=1, keepdims=True).T

    for start in range(0, nq, chunk_q):
        end = min(nq, start + chunk_q)
        q = queries[start:end]
        q_norms = np.sum(q ** 2, axis=1, keepdims=True)
        dists = q_norms + b_norms - 2.0 * np.matmul(q, base.T)
        kth = min(k - 1, dists.shape[1] - 1)
        idx = np.argpartition(dists, kth=kth, axis=1)[:, :k]
        gt[start:end] = idx.astype(np.int32, copy=False)

    return gt


def _write_ivecs(path: Path, ids: np.ndarray) -> None:
    if ids.ndim != 2:
        raise ValueError("ids must be a 2D array")
    nq, k = ids.shape
    if ids.dtype != np.int32:
        ids = ids.astype(np.int32)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        for i in range(nq):
            f.write(np.int32(k).tobytes())
            f.write(ids[i].tobytes())


def _compute_recall_at_k(gt: np.ndarray, retrieved: np.ndarray, k: int) -> float:
    nq = gt.shape[0]
    k_use = min(k, gt.shape[1], retrieved.shape[1])
    if k_use == 0:
        return 0.0
    hits = 0
    total = nq * k
    for i in range(nq):
        gt_set = set(int(x) for x in gt[i, :k_use])
        for j in range(k_use):
            if int(retrieved[i, j]) in gt_set:
                hits += 1
    return hits / float(total)


def _percentiles_us(vals_us: List[float]) -> Tuple[float, float, float]:
    if not vals_us:
        return 0.0, 0.0, 0.0
    xs = np.array(vals_us, dtype=np.float64)
    return (
        float(np.percentile(xs, 50)),
        float(np.percentile(xs, 95)),
        float(np.percentile(xs, 99)),
    )


def _run_hnswlib(
    *,
    base_path: Path,
    query_path: Path,
    groundtruth_path: Optional[Path],
    dataset_name: str,
    num_base: int,
    num_queries: int,
    dim: int,
    k: int,
    M: int,
    ef_construction: int,
    ef_search: int,
    json_out: Path,
) -> None:
    try:
        import hnswlib  # type: ignore
    except Exception as e:
        raise SystemExit(
            "hnswlib is required for Experiment 12. Install under WSL with `pip install hnswlib`."
        ) from e

    base_all = _read_fvecs(base_path)
    query_all = _read_fvecs(query_path)
    if base_all.shape[1] != dim:
        raise SystemExit(f"Base dim mismatch: expected {dim}, got {base_all.shape[1]}")
    if query_all.shape[1] != dim:
        raise SystemExit(f"Query dim mismatch: expected {dim}, got {query_all.shape[1]}")

    nb = min(num_base, base_all.shape[0])
    nq = min(num_queries, query_all.shape[0])

    base = base_all[:nb]
    queries = query_all[:nq]

    if groundtruth_path is not None:
        gt_full = _read_ivecs(groundtruth_path)
        if gt_full.shape[0] < nq:
            raise SystemExit(f"Groundtruth queries {gt_full.shape[0]} < num_queries {nq}")
        gt_eval = gt_full[:nq, :k]
    else:
        gt_eval = _compute_gt_knn_l2_chunked(base, queries, k)

    index = hnswlib.Index(space="l2", dim=dim)

    t0 = time.perf_counter()
    index.init_index(max_elements=nb, ef_construction=ef_construction, M=M)
    index.add_items(base, ids=np.arange(nb, dtype=np.int32))
    build_s = time.perf_counter() - t0

    index.set_ef(ef_search)

    lat_us: List[float] = []
    all_labels = np.empty((nq, k), dtype=np.int32)

    t1 = time.perf_counter()
    for i in range(nq):
        q0 = time.perf_counter()
        labels, _ = index.knn_query(queries[i : i + 1], k=k)
        q1 = time.perf_counter()
        lat_us.append((q1 - q0) * 1e6)
        all_labels[i] = labels[0]
    search_s = time.perf_counter() - t1

    recall = _compute_recall_at_k(gt_eval, all_labels, k)

    p50, p95, p99 = _percentiles_us(lat_us)

    effective_search_s = search_s
    effective_qps = float(nq) / effective_search_s if effective_search_s > 0 else 0.0
    qps_search = float(nq) / search_s if search_s > 0 else 0.0
    qps_total = float(nq) / (build_s + search_s) if (build_s + search_s) > 0 else 0.0

    out = {
        "config": {
            "dataset_name": dataset_name,
            "dimension": dim,
            "num_vectors": nb,
            "k": k,
            "ef_search": ef_search,
            "M": M,
            "ef_construction": ef_construction,
            "mode": "hnswlib",
        },
        "aggregate": {
            "k": k,
            "num_queries": nq,
            "recall_at_k": recall,
            "qps": qps_search,
            "qps_search": qps_search,
            "qps_total": qps_total,
            "latency_us_p50": p50,
            "latency_us_p95": p95,
            "latency_us_p99": p99,
            "build_time_s": build_s,
            "search_time_s": search_s,
            "effective_search_time_s": effective_search_s,
            "effective_qps": effective_qps,
            "io": {"num_reads": 0, "bytes_read": 0},
            "device_time_us": 0.0,
        },
    }

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(out, indent=2), encoding="utf-8")


def _run_hnswlib_synth(
    *,
    dataset_name: str,
    num_base: int,
    num_queries: int,
    dim: int,
    k: int,
    M: int,
    ef_construction: int,
    ef_search: int,
    json_out: Path,
    seed: int,
) -> None:
    """Run an HNSWLib baseline on a synthetic Gaussian dataset.

    This is used for the synthetic_gaussian portion of Experiment 12 so that
    the unified comparison plots include an HNSWLib point alongside DRAM,
    tiered, and ANN-in-SSD.
    """

    try:
        import hnswlib  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit(
            "hnswlib is required for Experiment 12. Install under WSL with `pip install hnswlib`."
        ) from e

    rng = np.random.default_rng(seed)
    base = rng.standard_normal(size=(num_base, dim)).astype(np.float32, copy=False)
    queries = rng.standard_normal(size=(num_queries, dim)).astype(np.float32, copy=False)

    gt_eval = _compute_gt_knn_l2_chunked(base, queries, k)

    index = hnswlib.Index(space="l2", dim=dim)

    t0 = time.perf_counter()
    index.init_index(max_elements=num_base, ef_construction=ef_construction, M=M)
    index.add_items(base, ids=np.arange(num_base, dtype=np.int32))
    build_s = time.perf_counter() - t0

    index.set_ef(ef_search)

    lat_us: List[float] = []
    all_labels = np.empty((num_queries, k), dtype=np.int32)

    t1 = time.perf_counter()
    for i in range(num_queries):
        q0 = time.perf_counter()
        labels, _ = index.knn_query(queries[i : i + 1], k=k)
        q1 = time.perf_counter()
        lat_us.append((q1 - q0) * 1e6)
        all_labels[i] = labels[0]
    search_s = time.perf_counter() - t1

    recall = _compute_recall_at_k(gt_eval, all_labels, k)
    p50, p95, p99 = _percentiles_us(lat_us)

    effective_search_s = search_s
    effective_qps = float(num_queries) / effective_search_s if effective_search_s > 0 else 0.0
    qps_search = float(num_queries) / search_s if search_s > 0 else 0.0
    qps_total = float(num_queries) / (build_s + search_s) if (build_s + search_s) > 0 else 0.0

    out = {
        "config": {
            "dataset_name": dataset_name,
            "dimension": dim,
            "num_vectors": num_base,
            "k": k,
            "ef_search": ef_search,
            "M": M,
            "ef_construction": ef_construction,
            "mode": "hnswlib",
        },
        "aggregate": {
            "k": k,
            "num_queries": num_queries,
            "recall_at_k": recall,
            "qps": qps_search,
            "qps_search": qps_search,
            "qps_total": qps_total,
            "latency_us_p50": p50,
            "latency_us_p95": p95,
            "latency_us_p99": p99,
            "build_time_s": build_s,
            "search_time_s": search_s,
            "effective_search_time_s": effective_search_s,
            "effective_qps": effective_qps,
            "io": {"num_reads": 0, "bytes_read": 0},
            "device_time_us": 0.0,
        },
    }

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(out, indent=2), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Experiment 12: unified cross-solution comparison")
    p.add_argument(
        "--quick",
        action="store_true",
        help="Run a smaller subset (SIFT20k + synthetic20k only).",
    )
    args = p.parse_args()

    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent
    project_dir = exp_dir.parent.parent

    bin_path = project_dir / "bin" / "benchmark_recall"
    if not bin_path.exists():
        raise SystemExit(f"benchmark_recall not found at {bin_path}; build benchmarks first.")

    results_raw = exp_dir / "results" / "raw"
    results_raw.mkdir(parents=True, exist_ok=True)

    # Common ANN parameters
    k = 10
    dim = 128

    # Common HNSW params (ours + hnswlib)
    M = 24
    ef_construction = 300
    ef_search = 512
    hnsw_build_threads = 8

    # Tiered SSD model
    ssd_base_latency_us = 80.0
    ssd_bw_GBps = 3.0
    ssd_num_channels = 4
    ssd_queue_depth = 64

    # Tiered cache fraction
    cache_frac = 0.25

    # ANN-SSD params
    ann_levels = ["L0", "L1", "L2", "L3"]
    ann_vectors_per_block = 128
    ann_portal_degree = 2
    ann_max_steps = 0

    seed = 42

    # SIFT paths
    sift_base = project_dir / "data" / "SIFT1M" / "sift" / "sift_base.fvecs"
    sift_query = project_dir / "data" / "SIFT1M" / "sift" / "sift_query.fvecs"
    sift_gt = project_dir / "data" / "SIFT1M" / "sift" / "sift_groundtruth.ivecs"

    if not sift_base.exists() or not sift_query.exists() or not sift_gt.exists():
        raise SystemExit("SIFT1M files not found under data/SIFT1M/sift/")

    sift_points = [(20000, 2000)]
    if not args.quick:
        sift_points.append((100000, 200))

    synth_points = [(20000, 2000)]
    if not args.quick:
        synth_points.append((100000, 2000))

    # 1) SIFT runs: hnswlib + our DRAM/tiered + ANN-SSD
    for nb, nq in sift_points:
        ds = "SIFT1M"
        tag = f"exp12_sift_nb{nb}_q{nq}_M{M}_efs{ef_search}"

        gt_subset = results_raw / f"{tag}_gt_k{k}.ivecs"
        if not gt_subset.exists():
            base_all = _read_fvecs(sift_base)
            query_all = _read_fvecs(sift_query)
            base = base_all[:nb]
            queries = query_all[:nq]
            gt = _compute_gt_knn_l2_chunked(base, queries, k)
            _write_ivecs(gt_subset, gt)

        # hnswlib
        out_h = results_raw / f"{tag}_mode-hnswlib.json"
        _run_hnswlib(
            base_path=sift_base,
            query_path=sift_query,
            groundtruth_path=gt_subset,
            dataset_name=ds,
            num_base=nb,
            num_queries=nq,
            dim=dim,
            k=k,
            M=M,
            ef_construction=ef_construction,
            ef_search=ef_search,
            json_out=out_h,
        )

        # ours DRAM
        out_d = results_raw / f"{tag}_mode-dram.json"
        cmd = [
            str(bin_path),
            "--mode",
            "dram",
            "--num-base",
            str(nb),
            "--num-queries",
            str(nq),
            "--dim",
            str(dim),
            "--k",
            str(k),
            "--ef-search",
            str(ef_search),
            "--M",
            str(M),
            "--ef-construction",
            str(ef_construction),
            "--hnsw-build-threads",
            str(hnsw_build_threads),
            "--seed",
            str(seed),
            "--dataset-name",
            ds,
            "--dataset-path",
            str(sift_base),
            "--query-path",
            str(sift_query),
            "--groundtruth-path",
            str(gt_subset),
            "--json-out",
            str(out_d),
        ]
        _run(cmd, project_dir)

        # ours tiered
        cap = max(1, int(nb * cache_frac))
        out_t = results_raw / f"{tag}_mode-tiered_cache{int(cache_frac*100)}.json"
        cmd = [
            str(bin_path),
            "--mode",
            "tiered",
            "--num-base",
            str(nb),
            "--num-queries",
            str(nq),
            "--dim",
            str(dim),
            "--k",
            str(k),
            "--ef-search",
            str(ef_search),
            "--M",
            str(M),
            "--ef-construction",
            str(ef_construction),
            "--hnsw-build-threads",
            str(hnsw_build_threads),
            "--seed",
            str(seed),
            "--cache-capacity",
            str(cap),
            "--cache-policy",
            "lru",
            "--ssd-base-latency-us",
            str(ssd_base_latency_us),
            "--ssd-internal-bw-GBps",
            str(ssd_bw_GBps),
            "--ssd-num-channels",
            str(ssd_num_channels),
            "--ssd-queue-depth",
            str(ssd_queue_depth),
            "--dataset-name",
            ds,
            "--dataset-path",
            str(sift_base),
            "--query-path",
            str(sift_query),
            "--groundtruth-path",
            str(gt_subset),
            "--json-out",
            str(out_t),
        ]
        _run(cmd, project_dir)

        # ANN-SSD: run both full-scan (max_steps=0) and a mid-steps config
        for lvl in ann_levels:
            # Full-scan / high-recall configuration (max_steps=0)
            out_a = results_raw / f"{tag}_mode-annssd_level-{lvl}.json"
            cmd = [
                str(bin_path),
                "--mode",
                "ann_ssd",
                "--num-base",
                str(nb),
                "--num-queries",
                str(nq),
                "--dim",
                str(dim),
                "--k",
                str(k),
                "--seed",
                str(seed),
                "--dataset-name",
                ds,
                "--dataset-path",
                str(sift_base),
                "--query-path",
                str(sift_query),
                "--groundtruth-path",
                str(gt_subset),
                "--ann-ssd-mode",
                "cheated",
                "--ann-hw-level",
                lvl,
                "--ann-vectors-per-block",
                str(ann_vectors_per_block),
                "--ann-max-steps",
                str(ann_max_steps),
                "--ann-portal-degree",
                str(ann_portal_degree),
                "--json-out",
                str(out_a),
            ]
            _run(cmd, project_dir)

            # Mid-steps configuration: ~0.5 * number_of_blocks to target ~0.85-0.9 recall
            num_blocks = (nb + ann_vectors_per_block - 1) // ann_vectors_per_block
            max_steps_mid = max(1, int(num_blocks * 0.5))
            out_a_mid = results_raw / f"{tag}_mode-annssd_level-{lvl}_steps{max_steps_mid}.json"
            cmd_mid = [
                str(bin_path),
                "--mode",
                "ann_ssd",
                "--num-base",
                str(nb),
                "--num-queries",
                str(nq),
                "--dim",
                str(dim),
                "--k",
                str(k),
                "--seed",
                str(seed),
                "--dataset-name",
                ds,
                "--dataset-path",
                str(sift_base),
                "--query-path",
                str(sift_query),
                "--groundtruth-path",
                str(gt_subset),
                "--ann-ssd-mode",
                "cheated",
                "--ann-hw-level",
                lvl,
                "--ann-vectors-per-block",
                str(ann_vectors_per_block),
                "--ann-max-steps",
                str(max_steps_mid),
                "--ann-portal-degree",
                str(ann_portal_degree),
                "--json-out",
                str(out_a_mid),
            ]
            _run(cmd_mid, project_dir)

            # High-steps configuration: ~0.95 * number_of_blocks to target ~0.95-0.99 recall
            max_steps_hi = max(1, int(num_blocks * 0.95))
            out_a_hi = results_raw / f"{tag}_mode-annssd_level-{lvl}_steps{max_steps_hi}.json"
            cmd_hi = [
                str(bin_path),
                "--mode",
                "ann_ssd",
                "--num-base",
                str(nb),
                "--num-queries",
                str(nq),
                "--dim",
                str(dim),
                "--k",
                str(k),
                "--seed",
                str(seed),
                "--dataset-name",
                ds,
                "--dataset-path",
                str(sift_base),
                "--query-path",
                str(sift_query),
                "--groundtruth-path",
                str(gt_subset),
                "--ann-ssd-mode",
                "cheated",
                "--ann-hw-level",
                lvl,
                "--ann-vectors-per-block",
                str(ann_vectors_per_block),
                "--ann-max-steps",
                str(max_steps_hi),
                "--ann-portal-degree",
                str(ann_portal_degree),
                "--json-out",
                str(out_a_hi),
            ]
            _run(cmd_hi, project_dir)

    # 2) Synthetic runs: our DRAM/tiered + ANN-SSD (no hnswlib)
    for nb, nq in synth_points:
        ds = "synthetic_gaussian"
        tag = f"exp12_synth_nb{nb}_q{nq}_M{M}_efs{ef_search}"

        # HNSWlib baseline on a Python-generated synthetic Gaussian dataset.
        out_h = results_raw / f"{tag}_mode-hnswlib.json"
        _run_hnswlib_synth(
            dataset_name=ds,
            num_base=nb,
            num_queries=nq,
            dim=dim,
            k=k,
            M=M,
            ef_construction=ef_construction,
            ef_search=ef_search,
            json_out=out_h,
            seed=seed,
        )

        out_d = results_raw / f"{tag}_mode-dram.json"
        cmd = [
            str(bin_path),
            "--mode",
            "dram",
            "--num-base",
            str(nb),
            "--num-queries",
            str(nq),
            "--dim",
            str(dim),
            "--k",
            str(k),
            "--ef-search",
            str(ef_search),
            "--M",
            str(M),
            "--ef-construction",
            str(ef_construction),
            "--hnsw-build-threads",
            str(hnsw_build_threads),
            "--seed",
            str(seed),
            "--dataset-name",
            ds,
            "--json-out",
            str(out_d),
        ]
        _run(cmd, project_dir)

        cap = max(1, int(nb * cache_frac))
        out_t = results_raw / f"{tag}_mode-tiered_cache{int(cache_frac*100)}.json"
        cmd = [
            str(bin_path),
            "--mode",
            "tiered",
            "--num-base",
            str(nb),
            "--num-queries",
            str(nq),
            "--dim",
            str(dim),
            "--k",
            str(k),
            "--ef-search",
            str(ef_search),
            "--M",
            str(M),
            "--ef-construction",
            str(ef_construction),
            "--hnsw-build-threads",
            str(hnsw_build_threads),
            "--seed",
            str(seed),
            "--cache-capacity",
            str(cap),
            "--cache-policy",
            "lru",
            "--ssd-base-latency-us",
            str(ssd_base_latency_us),
            "--ssd-internal-bw-GBps",
            str(ssd_bw_GBps),
            "--ssd-num-channels",
            str(ssd_num_channels),
            "--ssd-queue-depth",
            str(ssd_queue_depth),
            "--dataset-name",
            ds,
            "--json-out",
            str(out_t),
        ]
        _run(cmd, project_dir)

        for lvl in ann_levels:
            # Full-scan / high-recall configuration (max_steps=0)
            out_a = results_raw / f"{tag}_mode-annssd_level-{lvl}.json"
            cmd = [
                str(bin_path),
                "--mode",
                "ann_ssd",
                "--num-base",
                str(nb),
                "--num-queries",
                str(nq),
                "--dim",
                str(dim),
                "--k",
                str(k),
                "--seed",
                str(seed),
                "--dataset-name",
                ds,
                "--ann-ssd-mode",
                "cheated",
                "--ann-hw-level",
                lvl,
                "--ann-vectors-per-block",
                str(ann_vectors_per_block),
                "--ann-max-steps",
                str(ann_max_steps),
                "--ann-portal-degree",
                str(ann_portal_degree),
                "--json-out",
                str(out_a),
            ]
            _run(cmd, project_dir)

            # Mid-steps configuration: ~0.5 * number_of_blocks to target ~0.85-0.9 recall
            num_blocks = (nb + ann_vectors_per_block - 1) // ann_vectors_per_block
            max_steps_mid = max(1, int(num_blocks * 0.5))
            out_a_mid = results_raw / f"{tag}_mode-annssd_level-{lvl}_steps{max_steps_mid}.json"
            cmd_mid = [
                str(bin_path),
                "--mode",
                "ann_ssd",
                "--num-base",
                str(nb),
                "--num-queries",
                str(nq),
                "--dim",
                str(dim),
                "--k",
                str(k),
                "--seed",
                str(seed),
                "--dataset-name",
                ds,
                "--ann-ssd-mode",
                "cheated",
                "--ann-hw-level",
                lvl,
                "--ann-vectors-per-block",
                str(ann_vectors_per_block),
                "--ann-max-steps",
                str(max_steps_mid),
                "--ann-portal-degree",
                str(ann_portal_degree),
                "--json-out",
                str(out_a_mid),
            ]
            _run(cmd_mid, project_dir)

    print("\n[run_experiment12] wrote JSON logs to", results_raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
