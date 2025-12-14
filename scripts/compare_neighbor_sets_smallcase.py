#!/usr/bin/env python3
import argparse


def read_neighbors(path: str):
    neighbors = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                neighbors.append([])
                continue
            ids = [int(x) for x in line.split()]
            neighbors.append(ids)
    return neighbors


def main() -> None:
    p = argparse.ArgumentParser(description="Compare per-query neighbor sets from our HNSW vs hnswlib")
    p.add_argument("--ours", required=True, help="Path to neighbors file from benchmark_recall --per-query-out")
    p.add_argument("--hnswlib", required=True, help="Path to neighbors file from compare_hnswlib_sift.py --neighbors-out")
    p.add_argument("--k", type=int, default=10)
    args = p.parse_args()

    ours = read_neighbors(args.ours)
    lib = read_neighbors(args.hnswlib)

    if len(ours) != len(lib):
        raise SystemExit(f"Mismatched query counts: ours={len(ours)}, hnswlib={len(lib)}")

    nq = len(ours)
    k = args.k

    overlaps = []
    for i in range(nq):
        a = ours[i][:k]
        b = lib[i][:k]
        sa = set(a)
        sb = set(b)
        inter = len(sa & sb)
        overlaps.append(inter)

    avg_overlap = sum(overlaps) / float(nq)
    avg_recall_vs_lib = avg_overlap / float(k) if k > 0 else 0.0

    print(f"num_queries={nq}")
    print(f"avg_overlap = {avg_overlap:.3f} (out of k={k})")
    print(f"avg_fraction_overlap = {avg_recall_vs_lib:.4f}")

    # Show a few worst queries
    worst = sorted(range(nq), key=lambda i: overlaps[i])[:10]
    print("worst_queries (index: overlap / k, ours -> lib):")
    for qi in worst:
        o = overlaps[qi]
        a = ours[qi][:k]
        b = lib[qi][:k]
        print(f"  q={qi}: {o}/{k}, ours={a}, hnswlib={b}")


if __name__ == "__main__":
    main()
