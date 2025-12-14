# Experiment 10 Conclusions: ANN-in-SSD Design Space Exploration

This experiment explores ANN-in-SSD design parameters and their impact on recall vs modeled throughput.

## Setup (this run)

- Dataset: synthetic Gaussian (`NUM_BASE=20000`, `NUM_QUERIES=2000`, `DIM=128`)
- Hardware level: `L2`
- Simulator mode: `cheated`
- Sweep dimensions:
  - `vectors_per_block` (Kpb): {64, 128, 256}
  - `max_steps`: {16, 32, 64, 0}
  - `portal_degree` (P): {1, 2, 4}

## Main observations

- **Recall increases with `max_steps`**, at the cost of lower effective QPS.
  - For example at `Kpb=256`, recall rises from ~0.24 (`max_steps=16`) to ~0.83 (`max_steps=64`) to 1.0 (`max_steps=0`).
- **Smaller `Kpb` can inflate effective QPS** for small `max_steps` (since fewer vectors are processed per block), but recall remains low when `max_steps` is constrained.
- **Portal degree had limited effect in this sweep** compared to `max_steps` and `Kpb` (curves for P=1/2/4 are close for the same Kpb/steps).

## Quantitative snapshot

From `scripts/analyze_experiment10.py`:

- Full traversal (`max_steps=0`) reaches recall@10=1.0 across Kpb values, with effective QPS on the order of ~8.6k–10.2k.
- Constrained traversal shows the expected recall/throughput trade-off:
  - `Kpb=256, max_steps=64`: recall@10 ≈ 0.828, effective QPS ≈ 12.6k
  - `Kpb=128, max_steps=64`: recall@10 ≈ 0.418, effective QPS ≈ 23.5k
  - `Kpb=64, max_steps=64`: recall@10 ≈ 0.229, effective QPS ≈ 42.0k

## Outputs

- JSON logs: `results/raw/exp10_*.json`
- Plots: `results/plots/`
  - `exp10_recall_vs_effective_qps_P1.png`
  - `exp10_recall_vs_effective_qps_P2.png`
  - `exp10_recall_vs_effective_qps_P4.png`
