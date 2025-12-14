# Experiment 11 Conclusions: ANN-in-SSD Hardware Level Sensitivity

This experiment evaluates how modeled ANN-in-SSD hardware levels (`L0–L3`) change effective throughput under the same search configuration.

## Setup (from `scripts/experiment11.sh`)

- Dataset: synthetic Gaussian
- `num_queries = 2000`, `dim = 128`, `k = 10`
- Levels: `L0`, `L1`, `L2`, `L3`
- Simulation modes: `faithful` and `cheated`
- Fixed ANN-in-SSD configuration:
  - `vectors_per_block = 128`
  - `max_steps = 20`
  - `portal_degree = 2`

## Key observations (this run)

From `scripts/analyze_experiment11.py`:

- **Cheated effective QPS scales dramatically with hardware level**:
  - At `num_base=20000`, effective QPS increases from ~1.5k (L0 cheated) to ~4.5k (L1 cheated) to ~22k (L2 cheated) to ~89k (L3 cheated).
- **Faithful effective QPS is much closer across levels** in these small runs (often ~5k–7k), indicating the faithful simulator’s per-step overhead dominates and it should be treated primarily as a correctness/sanity mode.
- **Device time trends**:
  - Faithful runs show non-zero `device_time_us` and lower effective QPS; cheated runs can report near-zero device time for small `max_steps`, leading to very high modeled effective QPS.

## Outputs

- Plots:
  - `results/plots/exp11_effective_qps_vs_num_vectors.png`
  - `results/plots/exp11_device_time_vs_num_vectors.png`
- Raw logs:
  - `results/raw/annssd_nb-*_level-*_mode-*.json`

## Notes

- The `results/raw/` folder also contains additional cheated-only runs at `num_base=1,000,000` with varying `max_steps`, which can be used to study scaling and “fraction of blocks visited” behavior.
