# Experiment 9 Conclusions: ANN-in-SSD vs Tiered vs DRAM

This experiment compares the three main solutions on a common workload:

- DRAM-only HNSW (`mode=dram`)
- Tiered DRAM+SSD HNSW (`mode=tiered`)
- ANN-in-SSD simulator (`mode=ann_ssd`, `ann-ssd-mode=cheated`), across hardware levels

## Setup (this run)

- Dataset: synthetic Gaussian (`NUM_BASE=20000`, `NUM_QUERIES=2000`, `DIM=128`)
- Common search target: `k=10`
- DRAM/tiered HNSW parameters: `M=16`, `ef_construction=200`, `ef_search=100`
- Tiered cache: `CACHE_CAPACITY=10000` (50% of base set)
- ANN-in-SSD: levels `L0`, `L2`, `L3` (cheated/analytic)

## Quantitative snapshot

From `scripts/analyze_experiment9.py`:

- DRAM:

  - recall@10 ≈ 0.9381
  - QPS (wall) ≈ 110.1
  - effective QPS ≈ 3819.3
  - latency p50/p95/p99 ≈ 220.5 / 473.8 / 877.7 us

- Tiered:

  - recall@10 ≈ 0.9381
  - QPS (wall) ≈ 101.6
  - effective QPS ≈ 627.6
  - latency p50/p95/p99 ≈ 1167.1 / 2776.2 / 4749.2 us

- ANN-in-SSD:
  - L0:
    - recall@10 = 1.0
    - QPS (wall) ≈ 729.6
    - effective QPS ≈ 48.7
    - latency p50/p95/p99 ≈ 1162.0 / 2379.9 / 3825.1 us
  - L2:
    - recall@10 = 1.0
    - QPS (wall) ≈ 712.6
    - effective QPS ≈ 9606.2
    - latency p50/p95/p99 ≈ 1148.1 / 2373.1 / 4269.0 us
  - L3:
    - recall@10 = 1.0
    - QPS (wall) ≈ 811.4
    - effective QPS ≈ 28370.0
    - latency p50/p95/p99 ≈ 1107.6 / 1943.0 / 3751.7 us

## Interpretation

- **DRAM vs tiered**: Recall is identical in this configuration, but tiered has higher tail latency due to SSD misses and modeled device time.
- **ANN-in-SSD**: Wall-clock QPS appears higher than tiered/DRAM here, but the analytic model’s _effective QPS_ varies drastically by hardware level, reflecting how the simulator accounts for internal compute/bandwidth limits.
- This experiment primarily validates that the three modes can be run under a single harness with common logging, and that the simulator can be compared side-by-side with tiered and DRAM baselines.

## Outputs

- JSON logs: `results/raw/exp9_*.json`
- Plot: `results/plots/exp9_synthetic_gaussian_recall_qps.png`
