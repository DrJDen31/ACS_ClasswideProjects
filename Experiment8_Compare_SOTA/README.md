# Experiment 8: Comparison with State-of-the-Art

Compare our in-tree DRAM HNSW implementation against a fast external DRAM baseline (hnswlib) on SIFT subsets.

## Goals

- Provide a best-effort “SOTA-style” DRAM baseline without requiring external C++ projects (DiskANN) or heavyweight dependencies (FAISS).
- Run matching SIFT subsets and HNSW parameters.
- Compare recall, latency percentiles, build time, and effective QPS.

## Workload and configuration

- Dataset: SIFT1M
  - Base: `data/SIFT1M/sift/sift_base.fvecs`
  - Queries: `data/SIFT1M/sift/sift_query.fvecs`
- Subset points:
  - `num_base=20000, num_queries=2000`
  - `num_base=100000, num_queries=200`
- Parameters:
  - `dim=128`, `k=10`
  - `M=24`, `ef_construction=300`, `ef_search=512`

Ground truth is recomputed on each subset (brute-force L2) for both baselines to avoid the “full SIFT1M GT out-of-range” issue.

## How to run

From the project root under WSL:

1. Build benchmarks if needed:
   - `make benchmarks`
2. Ensure hnswlib is installed in WSL:
   - `pip install hnswlib`
3. Run Experiment 8:

```bash
cd experiments/Experiment8_Compare_SOTA
./scripts/experiment8.sh
```

This produces JSON logs in `results/raw/`:

- `exp8_hnswlib_*.json`
- `exp8_ours_dram_*.json`

## Analysis and plots

```bash
cd experiments/Experiment8_Compare_SOTA
python3 scripts/analyze_experiment8.py
```

Plots written to `results/plots/`:

- `exp8_recall_vs_effective_qps.png`
- `exp8_build_time_vs_num_vectors.png`

## Quantitative snapshot (this run)

From `scripts/analyze_experiment8.py`:

- 20k base, 2k queries:
  - Ours (DRAM): build ≈ 19.313s, eff QPS ≈ 1426.63, recall@10 ≈ 0.99990, p50 ≈ 647.85us
  - hnswlib: build ≈ 0.534s, eff QPS ≈ 2394.78, recall@10 ≈ 0.99995, p50 ≈ 365.57us

- 100k base, 200 queries:
  - Ours (DRAM): build ≈ 156.108s, eff QPS ≈ 691.90, recall@10 = 1.0, p50 ≈ 1344.12us
  - hnswlib: build ≈ 8.044s, eff QPS ≈ 1190.56, recall@10 = 1.0, p50 ≈ 727.94us

## Notes / caveats

- For our DRAM runs, build used the single-threaded path (default `benchmark_recall` build threads = 1). This experiment is primarily a “speed-gap” check against hnswlib; a follow-up refinement would be to re-run with `--hnsw-build-threads 8` to see how much of the build-time gap is parallelism vs implementation efficiency.
