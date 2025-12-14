# Experiment 11: ANN-in-SSD Hardware Level Sensitivity

Model ANN-in-SSD hardware levels `L0–L3` and compare how modeled compute/IO capabilities impact effective throughput and latency.

## What this measures

For each hardware level and simulator mode, measure:

- `recall@k`
- QPS and effective QPS (including modeled device time where applicable)
- latency percentiles
- `compute_time_s` and `device_time_us`

## How to run

From the project root under WSL:

```bash
cd experiments/Experiment11_AnnSSD_Hardware_Levels
./scripts/experiment11.sh
python3 scripts/analyze_experiment11.py
```

Optional (larger-scale cheated-only sweep for L3 where `max_steps` approximates a fraction of blocks):

```bash
cd experiments/Experiment11_AnnSSD_Hardware_Levels
./scripts/experiment11_fraction_sweep.sh
```

## Outputs

- Raw JSON logs: `results/raw/*.json`
- Plots: `results/plots/`
  - `exp11_effective_qps_vs_num_vectors.png`
  - `exp11_device_time_vs_num_vectors.png`

## Notes

- `faithful` is intended as a step-by-step simulator sanity check; `cheated` is an analytic mode intended for larger sweeps.
- The experiment directory also contains some additional raw JSONs for larger-`num_base` cheated-only sweeps.
