# Experiment 10: ANN-in-SSD Design Space Exploration

Explore ANN-in-SSD design parameters:

- Vectors per block (K), portal degree (P), neighbor degree (M), and `max_steps`.
- Measure recall@k, QPS, `avg_blocks_visited`, `avg_distances_computed`, and device time.

## How to run

From the project root under WSL:

```bash
cd experiments/Experiment10_AnnSSD_Design_Space
./scripts/experiment10.sh
python3 scripts/analyze_experiment10.py
```

The driver reads parameters from `config/experiment10.conf`.

## Current sweep (config default)

- Hardware level: `L2`
- Simulator mode: `cheated`
- `K_VALUES = {64, 128, 256}`
- `STEPS_VALUES = {16, 32, 64, 0}` (where `0` means full traversal)
- `PORTAL_VALUES = {1, 2, 4}`

## Outputs

- Raw JSON logs: `results/raw/exp10_*.json`
- Plots: `results/plots/`
  - `exp10_recall_vs_effective_qps_P1.png`
  - `exp10_recall_vs_effective_qps_P2.png`
  - `exp10_recall_vs_effective_qps_P4.png`
