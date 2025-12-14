# Experiment 2: Tiered vs DRAM

## What and why

- **What:** Compare pure DRAM HNSW (`mode=dram`) against Tiered HNSW (`mode=tiered`) on a common synthetic workload.
- **Why:** Quantify the impact of introducing a simulated SSD tier on:
  - recall@k,
  - QPS / effective QPS,
  - latency percentiles,
  - and I/O behavior (reads, bytes, modeled device time).

This experiment uses a **synthetic 128D Gaussian dataset** with 20k base vectors and 2k queries and sweeps **tiered cache capacity** as a fraction of the index size.

## Configuration

Common settings for all runs in this experiment:

- Dataset: synthetic Gaussian (generated inside `benchmark_recall`).
- `num_base = 20,000`, `num_queries = 2,000`, `dim = 128`.
- HNSW parameters: `M = 24`, `ef_construction = 300`, `ef_search = 256`, `k = 10`, `seed = 42`.
- Modes:
  - DRAM baseline: `mode = dram`.
  - Tiered runs: `mode = tiered`, with a configurable cache capacity (in vectors).

Tiered cache capacities used:

- 10% of index: `cache_capacity = 2,000` (label: `cache10`).
- 25% of index: `cache_capacity = 5,000` (label: `cache25`).
- 50% of index: `cache_capacity = 10,000` (label: `cache50`).
- 100% of index: `cache_capacity = 20,000` (label: `cache100`).

## How to run (Windows + WSL)

### 1. Ensure benchmarks are built

From the project root (`TrackB/`):

```powershell
wsl make -C /mnt/c/Users/jaden/OneDrive/Documents/RPI/Fall2025/AdvancedComputerSystems/Projects/TrackB benchmarks
```

This should produce `bin/benchmark_recall`.

### 2. Run Experiment 2 sweep

From the project root (`TrackB/`):

```powershell
wsl bash -lc 'cd /mnt/c/Users/jaden/OneDrive/Documents/RPI/Fall2025/AdvancedComputerSystems/Projects/TrackB/experiments/Experiment2_Tiered_vs_DRAM && ./scripts/experiment2.sh'
```

This script:

- Invokes `scripts/run_experiment2.py`.
- Runs the following configurations via `bin/benchmark_recall`:
  - `exp2_dram_nb20k_q2k_efs256` – DRAM baseline.
  - `exp2_tiered_cache10_nb20k_q2k_efs256` – Tiered with 10% cache.
  - `exp2_tiered_cache25_nb20k_q2k_efs256` – Tiered with 25% cache.
  - `exp2_tiered_cache50_nb20k_q2k_efs256` – Tiered with 50% cache.
  - `exp2_tiered_cache100_nb20k_q2k_efs256` – Tiered with 100% cache.
- Writes JSON logs into `results/raw/exp2_*.json`.
- Prints a quick summary (mode, recall@k, `qps`, `effective_qps`) for each new JSON.

Older, manually generated JSONs (`dram_20k.json`, `tiered_20k.json`, `tiered_sanity.json`) are preserved but are **not** part of the new sweep. The analysis script below focuses on the `exp2_*.json` files.

## How to analyze and visualize results

Use the dedicated analysis script to summarize and plot the DRAM vs tiered comparison:

```powershell
wsl bash -lc 'cd /mnt/c/Users/jaden/OneDrive/Documents/RPI/Fall2025/AdvancedComputerSystems/Projects/TrackB/experiments/Experiment2_Tiered_vs_DRAM && python3 scripts/analyze_experiment2.py'
```

This script:

- Loads all `results/raw/exp2_*.json` files.
- Prints a table with, per run:
  - mode (`dram` or `tiered`),
  - approximate cache fraction (for tiered),
  - recall@k,
  - `qps` (wall-clock QPS),
  - `effective_qps` (search time + modeled device time),
  - build and search times,
  - modeled device time (`device_time_us`),
  - `io.num_reads` and `io.bytes_read`.
- Produces plots in `results/plots/`:
  - `exp2_recall_effective_qps.png` – recall@k and `effective_qps` vs configuration (DRAM plus multiple cache sizes).
  - `exp2_io_per_query_vs_cache.png` – I/O per query (reads/query and bytes/query) vs tiered cache size.

These plots give a quick visual comparison of DRAM vs tiered performance and the effect (or lack of effect) of cache size on I/O.

## Files produced by this experiment

- **Raw JSON logs (new sweep):** `results/raw/exp2_*.json`

  - `exp2_dram_nb20k_q2k_efs256.json` – DRAM baseline.
  - `exp2_tiered_cache10_nb20k_q2k_efs256.json` – Tiered, 10% cache.
  - `exp2_tiered_cache25_nb20k_q2k_efs256.json` – Tiered, 25% cache.
  - `exp2_tiered_cache50_nb20k_q2k_efs256.json` – Tiered, 50% cache.
  - `exp2_tiered_cache100_nb20k_q2k_efs256.json` – Tiered, 100% cache.

- **Legacy JSONs (earlier manual runs):**

  - `results/dram_20k.json`, `results/tiered_20k.json`, `results/tiered_sanity.json` – earlier synthetic snapshots; useful for historical comparison but not used by the automated analysis.

- **Plots:**

  - `results/plots/exp2_recall_effective_qps.png`
  - `results/plots/exp2_io_per_query_vs_cache.png`

- **Conclusions:**
  - `CONCLUSIONS.md` – high-level interpretation of the DRAM vs tiered results and observations about cache-size effects and SSD device modeling.

Refer to `CONCLUSIONS.md` in this directory for a narrative summary suitable for the final report.
