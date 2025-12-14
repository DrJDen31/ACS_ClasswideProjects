# Experiment 8 Conclusions: Comparison with State-of-the-Art

This experiment compares our in-tree DRAM HNSW implementation against a fast external DRAM baseline (hnswlib) on SIFT subsets.

## Setup (summary)

- Dataset: SIFT1M base/query vectors.
- SIFT subset points:
  - `num_base=20000, num_queries=2000`
  - `num_base=100000, num_queries=200`
- Parameters: `dim=128`, `k=10`, `M=24`, `ef_construction=300`, `ef_search=512`.
- Ground truth: recomputed on each subset (brute-force L2) for both baselines.

## Quantitative snapshot

From `scripts/analyze_experiment8.py`:

- 20k base, 2k queries:
  - Ours (DRAM): build ≈ 19.313s, eff QPS ≈ 1426.63, recall@10 ≈ 0.99990, p50/p95/p99 ≈ 647.85/948.48/1622.95 us
  - hnswlib: build ≈ 0.534s, eff QPS ≈ 2394.78, recall@10 ≈ 0.99995, p50/p95/p99 ≈ 365.57/681.55/1504.18 us

- 100k base, 200 queries:
  - Ours (DRAM): build ≈ 156.108s, eff QPS ≈ 691.90, recall@10 = 1.0, p50/p95/p99 ≈ 1344.12/2377.86/3711.09 us
  - hnswlib: build ≈ 8.044s, eff QPS ≈ 1190.56, recall@10 = 1.0, p50/p95/p99 ≈ 727.94/1449.19/3588.92 us

## Interpretation

- **Quality parity**: At both subset sizes, hnswlib and our implementation achieve essentially identical recall under these parameters.
- **Speed gap**:
  - hnswlib is substantially faster on build time (e.g., ~0.53s vs ~19.3s at 20k; ~8.0s vs ~156s at 100k).
  - hnswlib also delivers higher effective QPS and lower latency p50/p95.
- This supports treating hnswlib as an engineering upper bound for DRAM HNSW performance when interpreting tiered and ANN-in-SSD results.

## Outputs

- JSON logs: `results/raw/exp8_*.json`
- Plots: `results/plots/exp8_recall_vs_effective_qps.png`, `results/plots/exp8_build_time_vs_num_vectors.png`

## Notes / caveats

- Our C++ run in this experiment used the single-threaded build path (`hnsw_build_threads=1` default). A follow-up refinement is to re-run our DRAM baseline with `--hnsw-build-threads 8` to see how much of the build-time gap is explained by parallelism vs implementation details.
- hnswlib must be installed in the WSL Python environment.
