#!/usr/bin/env python3
import argparse
import time
from typing import Tuple

import numpy as np

try:
    import hnswlib
except ImportError as e:
    raise SystemExit("hnswlib is required. Install with `pip install hnswlib`.") from e


def read_fvecs(path: str) -> np.ndarray:
    """Load a fvecs file into a float32 numpy array of shape (n, d)."""
    with open(path, "rb") as f:
        data = f.read()
    if not data:
        raise ValueError(f"Empty fvecs file: {path}")

    # Each vector: int32 dim + dim * float32
    dim = np.frombuffer(data, dtype=np.int32, count=1)[0]
    if dim <= 0:
        raise ValueError(f"Invalid dim {dim} in fvecs file {path}")

    record_size = 4 + dim * 4
    if len(data) % record_size != 0:
        raise ValueError(
            f"File size {len(data)} not divisible by record size {record_size} for dim {dim}"
        )

    n = len(data) // record_size
    arr = np.frombuffer(data, dtype=np.int32).reshape(n, 1 + dim)
    # First column is dim, remaining are floats
    vecs = arr[:, 1:].view(np.float32)
    return vecs.copy()


def read_ivecs(path: str) -> np.ndarray:
    """Load an ivecs file into an int32 numpy array of shape (n, k)."""
    with open(path, "rb") as f:
        data = f.read()
    if not data:
        raise ValueError(f"Empty ivecs file: {path}")

    dim = np.frombuffer(data, dtype=np.int32, count=1)[0]
    if dim <= 0:
        raise ValueError(f"Invalid dim {dim} in ivecs file {path}")

    record_size = 4 + dim * 4
    if len(data) % record_size != 0:
        raise ValueError(
            f"File size {len(data)} not divisible by record size {record_size} for dim {dim}"
        )

    n = len(data) // record_size
    arr = np.frombuffer(data, dtype=np.int32).reshape(n, 1 + dim)
    ids = arr[:, 1:]
    return ids.copy()


def compute_recall_at_k(
    gt: np.ndarray,  # shape (nq, k_gt)
    retrieved: np.ndarray,  # shape (nq, k)
    k: int,
) -> float:
    """Compute average recall@k over all queries.

    Mirrors the C++ metric: use the first min(k, gt_len) true neighbors
    and first min(k, retrieved_len) returned neighbors.
    """

    nq, k_gt = gt.shape
    k_use = min(k, k_gt, retrieved.shape[1])
    if k_use == 0:
        return 0.0

    hits = 0
    total = nq * k
    for i in range(nq):
        gt_set = set(gt[i, :k_use].tolist())
        for j in range(k_use):
            if retrieved[i, j] in gt_set:
                hits += 1
    return hits / float(total)


def main() -> None:
    p = argparse.ArgumentParser(description="Compare hnswlib on SIFT subsets")
    p.add_argument("--base", required=True, help="Path to sift_base.fvecs")
    p.add_argument("--query", required=True, help="Path to sift_query.fvecs")
    p.add_argument("--groundtruth", required=False, help="Path to sift_groundtruth.ivecs")
    p.add_argument("--num-base", type=int, default=20000)
    p.add_argument("--num-queries", type=int, default=2000)
    p.add_argument("--dim", type=int, default=128)
    p.add_argument("--k", type=int, default=10)
    p.add_argument("--M", type=int, default=24)
    p.add_argument("--ef-construction", type=int, default=300)
    p.add_argument("--ef-search", type=int, default=512)
    p.add_argument(
        "--neighbors-out",
        required=False,
        default="",
        help="Optional path to write per-query neighbor IDs (one line per query, space-separated)",
    )
    args = p.parse_args()

    print("[compare_hnswlib_sift] loading base from", args.base)
    base = read_fvecs(args.base)
    if base.shape[1] != args.dim:
        raise SystemExit(f"Base dim mismatch: expected {args.dim}, got {base.shape[1]}")

    num_base = min(args.num_base, base.shape[0])
    base = base[:num_base]
    print(f"  using num_base={num_base}")

    print("[compare_hnswlib_sift] loading queries from", args.query)
    queries = read_fvecs(args.query)
    if queries.shape[1] != args.dim:
        raise SystemExit(f"Query dim mismatch: expected {args.dim}, got {queries.shape[1]}")

    num_queries = min(args.num_queries, queries.shape[0])
    queries = queries[:num_queries]
    print(f"  using num_queries={num_queries}")

    gt = None
    if args.groundtruth:
        print("[compare_hnswlib_sift] loading groundtruth from", args.groundtruth)
        gt_full = read_ivecs(args.groundtruth)
        if gt_full.shape[0] < num_queries:
            raise SystemExit(
                f"Groundtruth queries {gt_full.shape[0]} < num_queries {num_queries}"
            )
        gt_full = gt_full[:num_queries]
        # Filter to indices within the subset [0, num_base)
        mask = gt_full < num_base
        # Replace out-of-range with -1 and drop them when computing recall
        gt = np.where(mask, gt_full, -1)
    else:
        print("[compare_hnswlib_sift] no groundtruth provided; will compute brute-force GT")
        # Brute-force distances for ground truth (only feasible for small num_base)
        dists = np.matmul(
            queries,
            base.T,
        )  # cosine/IP would need different handling; here we use L2 via norms
        # For L2, we actually want squared distances; but for ranking, any monotone
        # transform is fine. If you want exact L2, compute ||q-b||^2 explicitly.
        # Here, reuse a simple implementation for clarity:
        q_norms = np.sum(queries ** 2, axis=1, keepdims=True)
        b_norms = np.sum(base ** 2, axis=1, keepdims=True).T
        dists = q_norms + b_norms - 2.0 * np.matmul(queries, base.T)
        order = np.argsort(dists, axis=1)
        gt = order[:, : args.k]

    print("[compare_hnswlib_sift] building hnswlib index...")
    index = hnswlib.Index(space="l2", dim=args.dim)

    t0 = time.time()
    index.init_index(max_elements=num_base, ef_construction=args.ef_construction, M=args.M)
    index.add_items(base, ids=np.arange(num_base, dtype=np.int32))
    build_time = time.time() - t0
    print(f"  build_time_s={build_time:.4f}")

    index.set_ef(args.ef_search)

    print("[compare_hnswlib_sift] searching...")
    t1 = time.time()
    labels, _ = index.knn_query(queries, k=args.k)
    search_time = time.time() - t1

    if args.neighbors_out:
        with open(args.neighbors_out, "w") as f:
            for row in labels:
                f.write(" ".join(str(int(x)) for x in row))
                f.write("\n")

    # Compute recall, ignoring gt entries that were -1 (out-of-range)
    if gt is not None:
        # Replace -1 with a large dummy id that won't match
        gt_eval = np.where(gt >= 0, gt, num_base + 1)
        recall = compute_recall_at_k(gt_eval, labels, args.k)
    else:
        recall = 0.0

    qps_total = num_queries / (build_time + search_time)
    qps_search = num_queries / search_time if search_time > 0 else 0.0

    print("[compare_hnswlib_sift] results:")
    print(f"  recall@{args.k} = {recall:.6f}")
    print(f"  build_time_s = {build_time:.4f}")
    print(f"  search_time_s = {search_time:.4f}")
    print(f"  total_QPS = {qps_total:.3f}")
    print(f"  search_QPS = {qps_search:.3f}")


if __name__ == "__main__":
    main()
