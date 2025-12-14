# Experiment 12 Conclusions: Unified Cross-Solution Comparison

This experiment compares all solutions under a single harness and shared parameters, producing a single set of JSON logs and cross-solution plots.

## Setup (this run)

- HNSW parameters (DRAM + tiered): `M=24`, `ef_construction=300`, `ef_search=512`
- Tiered cache: `cache_frac=0.25` (capacity derived as `num_base * 0.25`)
- Tiered SSD model: `base_latency_us=80`, `bw=3 GB/s`, `channels=4`, `queue_depth=64`
- ANN-in-SSD: cheated/analytic mode, levels `L0–L3`, `vectors_per_block=128`, `portal_degree=2`

Datasets / scale points:

- SIFT1M subset:
  - `num_base=20k`, `num_queries=2k`
  - `num_base=100k`, `num_queries=200`
- Synthetic Gaussian:
  - `num_base=20k`, `num_queries=2k`
  - `num_base=100k`, `num_queries=2k`

## Key observations (from generated tables/plots)

- **Tiered vs DRAM**:
  - Tiered achieves similar recall to DRAM at the same HNSW parameters, but its effective QPS drops significantly due to modeled SSD device time (miss-driven).
  - Example (synthetic, `num_base=100k`): DRAM effective QPS ~`368`, tiered ~`53` with much higher p50 latency.
- **ANN-in-SSD hardware levels move modeled throughput**:
  - In cheated/analytic mode, effective QPS increases strongly with hardware level (L0 → L3) for the same `num_base`.
  - Example (synthetic, `num_base=20k`): L0 ~`49` eff QPS vs L3 ~`28370` eff QPS.
- **Cross-solution sanity**:
  - On synthetic workloads, DRAM and tiered reach high recall (~0.98–1.0) at the chosen parameters.
  - On SIFT subsets, absolute recall values are lower because the unified harness uses the provided SIFT1M ground-truth and filters out-of-range IDs when `num_base < 1M`. This is consistent across solutions within this experiment and mainly impacts the absolute recall scale.

## Plots

- `results/plots/exp12_SIFT1M_recall_vs_effective_qps.png`
- `results/plots/exp12_synthetic_gaussian_recall_vs_effective_qps.png`
