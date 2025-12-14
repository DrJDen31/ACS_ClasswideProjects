#!/usr/bin/env python3
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


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


def _compute_gt_knn_l2_chunked(base: np.ndarray, queries: np.ndarray, k: int, chunk_q: int = 200) -> np.ndarray:
    nq = queries.shape[0]
    gt = np.empty((nq, k), dtype=np.int32)
    for start in range(0, nq, chunk_q):
        end = min(nq, start + chunk_q)
        q = queries[start:end]
        q_norms = np.sum(q ** 2, axis=1, keepdims=True)
        b_norms = np.sum(base ** 2, axis=1, keepdims=True).T
        dists = q_norms + b_norms - 2.0 * np.matmul(q, base.T)
        order = np.argsort(dists, axis=1)
        gt[start:end] = order[:, :k]
    return gt


def _compute_recall_at_k(gt: np.ndarray, retrieved: np.ndarray, k: int) -> float:
    nq = gt.shape[0]
    hits = 0
    for i in range(nq):
        gt_set = set(int(x) for x in gt[i, :k])
        for j in range(min(k, retrieved.shape[1])):
            if int(retrieved[i, j]) in gt_set:
                hits += 1
    return hits / float(nq * k)


def _percentiles_us(vals_us: List[float]) -> Tuple[float, float, float]:
    if not vals_us:
        return 0.0, 0.0, 0.0
    xs = np.array(vals_us, dtype=np.float64)
    return (
        float(np.percentile(xs, 50)),
        float(np.percentile(xs, 95)),
        float(np.percentile(xs, 99)),
    )


def _run(cmd: List[str], cwd: Path) -> None:
    print("\n[run_experiment8] exec:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if proc.returncode != 0:
        if proc.stdout:
            sys.stderr.write(proc.stdout)
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)
    if proc.stdout:
        sys.stdout.write(proc.stdout)


def _run_hnswlib_sift(
    base_path: Path,
    query_path: Path,
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
            "hnswlib is required for Experiment 8. Install under WSL with `pip install hnswlib`."
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

    gt = _compute_gt_knn_l2_chunked(base, queries, k)

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

    recall = _compute_recall_at_k(gt, all_labels, k)

    p50, p95, p99 = _percentiles_us(lat_us)

    effective_search_s = search_s
    effective_qps = float(nq) / effective_search_s if effective_search_s > 0 else 0.0
    qps_search = float(nq) / search_s if search_s > 0 else 0.0
    qps_total = float(nq) / (build_s + search_s) if (build_s + search_s) > 0 else 0.0

    out = {
        "config": {
            "dataset_name": "SIFT1M",
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


def main() -> int:
    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent
    project_dir = exp_dir.parent.parent

    bin_path = project_dir / "bin" / "benchmark_recall"
    if not bin_path.exists():
        raise SystemExit(f"benchmark_recall not found at {bin_path}; build benchmarks first.")

    results_raw = exp_dir / "results" / "raw"
    results_raw.mkdir(parents=True, exist_ok=True)

    base_path = project_dir / "data" / "SIFT1M" / "sift" / "sift_base.fvecs"
    query_path = project_dir / "data" / "SIFT1M" / "sift" / "sift_query.fvecs"
    if not base_path.exists():
        raise SystemExit(f"SIFT base file not found: {base_path}")
    if not query_path.exists():
        raise SystemExit(f"SIFT query file not found: {query_path}")

    dim = 128
    k = 10
    M = 24
    ef_construction = 300
    ef_search = 512
    seed = 42

    # Keep brute-force GT feasible by scaling num_queries down for larger subsets.
    # Add an intermediate point so scaling trends are clearer in Experiment 8 plots.
    sweep = [
        (20000, 2000),
        (50000, 400),
        (100000, 200),
    ]

    for (num_base, num_queries) in sweep:
        # hnswlib
        out_h = results_raw / f"exp8_hnswlib_sift_nb{num_base}_q{num_queries}_M{M}_efc{ef_construction}_efs{ef_search}.json"
        _run_hnswlib_sift(
            base_path=base_path,
            query_path=query_path,
            num_base=num_base,
            num_queries=num_queries,
            dim=dim,
            k=k,
            M=M,
            ef_construction=ef_construction,
            ef_search=ef_search,
            json_out=out_h,
        )
        print(f"[run_experiment8] wrote {out_h}")

        # our DRAM HNSW
        out_o = results_raw / f"exp8_ours_dram_sift_nb{num_base}_q{num_queries}_M{M}_efc{ef_construction}_efs{ef_search}.json"
        cmd = [
            str(bin_path),
            "--mode",
            "dram",
            "--num-base",
            str(num_base),
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
            "--seed",
            str(seed),
            "--dataset-name",
            "SIFT1M",
            "--dataset-path",
            str(base_path),
            "--query-path",
            str(query_path),
            # omit groundtruth-path so C++ recomputes GT on the subset
            "--json-out",
            str(out_o),
        ]
        _run(cmd, project_dir)

    print("\n[run_experiment8] Summary of new JSON results:")
    for p in sorted(results_raw.glob("exp8_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        cfg = data.get("config", {})
        agg = data.get("aggregate", {})

        num_q = agg.get("num_queries") or cfg.get("num_queries") or 0
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
        if qps_total is None:
            qps_total = agg.get("qps")

        print(
            f"  {p.name}: mode={cfg.get('mode')}, nb={cfg.get('num_vectors')}, "
            f"recall@k={agg.get('recall_at_k')}, build_s={agg.get('build_time_s')}, "
            f"qps_search={qps_search}, qps_total={qps_total}, eff_qps={agg.get('effective_qps')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
