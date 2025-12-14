# Experiment 7: Scaling

Study scaling behavior as dataset size grows.

## Goals

- Measure how **build time** and **effective QPS** scale with `num_base`.
- Compare **DRAM HNSW** (`mode=dram`) against **tiered HNSW** (`mode=tiered`, LRU) under a fixed SSD profile.

## Workload and configuration

- Dataset: SIFT1M
  - Base: `data/SIFT1M/sift/sift_base.fvecs`
  - Queries: `data/SIFT1M/sift/sift_query.fvecs`
  - Ground truth: `data/SIFT1M/sift/sift_groundtruth.ivecs`
- Query count: `num_queries = 2000`
- `dim = 128`, `k = 10`
- HNSW parameters:
  - `M = 24`
  - `ef_construction = 300`
  - `ef_search = 512`
  - `hnsw_build_threads = 8`
- Tiered SSD profile (NVMe Gen3-like):
  - `ssd_base_read_latency_us = 80.0`
  - `ssd_internal_read_bandwidth_GBps = 3.0`
  - `ssd_num_channels = 4`
  - `ssd_queue_depth = 64`
- Tiered cache sizing:
  - fixed cache fraction `cache_frac = 0.25` (25%)

## Scaling sweep

- DRAM runs (`mode=dram`):
  - `num_base ∈ {20000, 100000, 500000, 1000000}`
- Tiered runs (`mode=tiered`):
  - `num_base ∈ {20000, 100000, 500000}`
  - cache = 25% of `num_base`

## How to run

From the project root under WSL:

1. Build the benchmarks if needed:
   - `make benchmarks`
2. Run the Experiment 7 driver:

```bash
cd experiments/Experiment7_Scaling
./scripts/experiment7.sh
```

This writes JSON logs to `results/raw/exp7_*.json`.

## Analysis and plots

```bash
cd experiments/Experiment7_Scaling
python3 scripts/analyze_experiment7.py
```

This prints a summary table and writes plots to `results/plots/`:

- `exp7_build_time_vs_num_vectors.png`
- `exp7_effective_qps_vs_num_vectors.png`

## Quantitative snapshot (this run)

From `scripts/analyze_experiment7.py`:

- DRAM:
  - 20k: build ≈ 2.81s, effective QPS ≈ 1524.97, recall@10 ≈ 0.228
  - 100k: build ≈ 27.75s, effective QPS ≈ 669.42, recall@10 ≈ 0.849
  - 500k: build ≈ 280.40s, effective QPS ≈ 395.79, recall@10 ≈ 0.998
  - 1M: build ≈ 642.04s, effective QPS ≈ 332.25, recall@10 ≈ 0.999
- Tiered (25% cache):
  - 20k: build ≈ 3.17s, effective QPS ≈ 242.53, recall@10 ≈ 0.228
  - 100k: build ≈ 29.55s, effective QPS ≈ 112.48, recall@10 ≈ 0.849
  - 500k: build ≈ 271.38s, effective QPS ≈ 54.79, recall@10 ≈ 0.999

## Notes / caveats

- The SIFT ground-truth file is generated for the full 1M base. When running on smaller `num_base` subsets, many of the true nearest neighbors fall outside the subset and are filtered out, which can make the reported `recall@10` for small `num_base` appear artificially low (notably at 20k and 100k). The 500k and 1M points are much less affected.
- The main scaling signals we use in this experiment are build time and throughput trends; for strict recall-vs-scale comparisons on subsets, the ground truth should be recomputed for each subset.
