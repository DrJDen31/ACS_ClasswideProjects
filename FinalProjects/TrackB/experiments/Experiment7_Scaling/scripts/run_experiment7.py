#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


def _run(cmd, cwd: Path) -> None:
    print("\n[run_experiment7] exec:", " ".join(cmd))
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
        raise ValueError(f"Bad fvecs length for {path}")
    n = len(data) // record_size
    arr = np.frombuffer(data, dtype=np.int32).reshape(n, 1 + int(dim))
    vecs = arr[:, 1:].view(np.float32)
    return vecs.copy()


def _compute_gt_knn_l2_chunked(
    base: np.ndarray, queries: np.ndarray, k: int, chunk_q: int = 100
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Experiment 7 scaling driver")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only the smaller sweep (20k and 100k) for faster validation.",
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent
    project_dir = exp_dir.parent.parent

    bin_path = project_dir / "bin" / "benchmark_recall"
    if not bin_path.exists():
        raise SystemExit(f"benchmark_recall not found at {bin_path}; build benchmarks first.")

    results_raw = exp_dir / "results" / "raw"
    results_raw.mkdir(parents=True, exist_ok=True)

    dataset_base = project_dir / "data" / "SIFT1M" / "sift" / "sift_base.fvecs"
    dataset_query = project_dir / "data" / "SIFT1M" / "sift" / "sift_query.fvecs"
    dataset_gt = project_dir / "data" / "SIFT1M" / "sift" / "sift_groundtruth.ivecs"
    if not dataset_base.exists():
        raise SystemExit(f"SIFT base file not found: {dataset_base}")
    if not dataset_query.exists():
        raise SystemExit(f"SIFT query file not found: {dataset_query}")
    if not dataset_gt.exists():
        raise SystemExit(f"SIFT groundtruth file not found: {dataset_gt}")

    dim = 128
    k = 10
    ef_search = 512
    M = 24
    ef_construction = 300
    build_threads = 8
    seed = 42

    ssd_base_latency_us = 80.0
    ssd_bw_GBps = 3.0
    ssd_num_channels = 4
    ssd_queue_depth = 64

    # Scaling points. Tiered runs are more expensive; keep them to a smaller subset.
    dram_num_bases = [20000, 100000, 500000, 1000000]
    tiered_num_bases = [20000, 100000, 500000]
    if args.quick:
        dram_num_bases = [20000, 100000]
        tiered_num_bases = [20000, 100000]

    num_queries = 2000
    cache_frac = 0.25

    runs = []

    for nb in dram_num_bases:
        runs.append(
            {
                "name": f"exp7_dram_sift_nb{nb}_q{num_queries}_efs{ef_search}",
                "mode": "dram",
                "num_base": nb,
                "cache_capacity": None,
            }
        )

    for nb in tiered_num_bases:
        cap = max(1, int(nb * cache_frac))
        label = int(cache_frac * 100)
        runs.append(
            {
                "name": f"exp7_tiered_sift_nb{nb}_cache{label}_q{num_queries}_efs{ef_search}",
                "mode": "tiered",
                "num_base": nb,
                "cache_capacity": cap,
            }
        )

    for cfg in runs:
        json_out = results_raw / f"{cfg['name']}.json"

        gt_path = dataset_gt
        if cfg["num_base"] <= 100000:
            gt_path = results_raw / f"exp7_sift_nb{cfg['num_base']}_q{num_queries}_gt_k{k}.ivecs"
            if not gt_path.exists():
                base_all = _read_fvecs(dataset_base)
                query_all = _read_fvecs(dataset_query)
                base = base_all[: cfg["num_base"]]
                queries = query_all[:num_queries]
                gt = _compute_gt_knn_l2_chunked(base, queries, k)
                _write_ivecs(gt_path, gt)

        cmd = [
            str(bin_path),
            "--mode",
            cfg["mode"],
            "--num-base",
            str(cfg["num_base"]),
            "--num-queries",
            str(num_queries),
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
            str(build_threads),
            "--seed",
            str(seed),
            "--dataset-name",
            "SIFT1M",
            "--dataset-path",
            str(dataset_base),
            "--query-path",
            str(dataset_query),
            "--groundtruth-path",
            str(gt_path),
            "--json-out",
            str(json_out),
        ]

        if cfg["mode"] == "tiered" and cfg["cache_capacity"] is not None:
            cmd.extend(
                [
                    "--cache-capacity",
                    str(cfg["cache_capacity"]),
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
                ]
            )

        _run(cmd, project_dir)

    print("\n[run_experiment7] Summary of new JSON results:")
    for p in sorted(results_raw.glob("exp7_*.json")):
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        cfg = data.get("config", {})
        agg = data.get("aggregate", {})

        num_q = agg.get("num_queries") or cfg.get("num_queries") or 0
        build_s = agg.get("build_time_s")
        search_s = agg.get("search_time_s")

        qps_search = agg.get("qps_search")
        if qps_search is None and num_q and search_s is not None:
            try:
                s = float(search_s)
                if s > 0.0:
                    qps_search = float(num_q) / s
            except Exception:
                qps_search = None
        if qps_search is None:
            qps_search = agg.get("qps")

        qps_total = agg.get("qps_total")
        if qps_total is None and num_q and build_s is not None and search_s is not None:
            try:
                t = float(build_s) + float(search_s)
                if t > 0.0:
                    qps_total = float(num_q) / t
            except Exception:
                qps_total = None
        if qps_total is None:
            qps_total = agg.get("qps")

        print(
            f"  {p.name}: mode={cfg.get('mode')}, nb={cfg.get('num_vectors')}, cache={cfg.get('cache_capacity')}, "
            f"recall@k={agg.get('recall_at_k')}, build_s={agg.get('build_time_s')}, "
            f"qps_search={qps_search}, qps_total={qps_total}, eff_qps={agg.get('effective_qps')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
