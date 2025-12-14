# Experiment 1: DRAM Baseline

DRAM-only HNSW baseline on synthetic and real (e.g., SIFT1M) datasets.

- Sweep `ef_search` and possibly other HNSW parameters on a small synthetic dataset.
- Run a tuned DRAM HNSW configuration on full SIFT1M.
- Measure `recall@k`, QPS, latency percentiles.
- Use JSON logs from `benchmark_recall` (and this experiment’s driver) in `mode=dram`.

## What and why

- **What:** Establish a **trusted DRAM-only HNSW baseline** for both synthetic Gaussian data and the real SIFT1M dataset.
- **Why:** All tiered and ANN-in-SSD experiments later in the project need a clear answer to:
  - “How good can DRAM HNSW be on its own (recall/latency/QPS)?”
  - “How much performance/quality do we lose or gain when we introduce SSD, tiering, or ANN-in-SSD designs?”

This experiment produces:

- A recall–vs–`ef_search` curve on synthetic data.
- A tuned full SIFT1M DRAM baseline with near-perfect recall.
- Plots and tables that will be reused when interpreting later experiments.

## How to run the synthetic sweep

The synthetic sweep is configured via `config/experiment1.conf` and run through the generic experiment driver `scripts/experiment1.sh`.

Configuration (current defaults):

- `MODE="dram"`
- `NUM_BASE = 10000`
- `NUM_QUERIES = 1000`
- `DIM = 128`
- `K = 10`
- `M = 16`
- `EF_CONSTRUCTION = 200`
- `EF_SEARCH = 100` (base value, overridden by sweep)
- `SWEEP_EF_SEARCH = "16 32 64 128 256"`

Each sweep point runs `benchmark_recall` once with a different `ef_search` and writes a JSON file to `results/raw/` with a suffix encoding the parameter value (e.g., `..._EF_SEARCH-0016.json`).

### Commands (Windows + WSL)

From a PowerShell prompt in the project root (`TrackB/`):

1. **Build benchmarks (once):**

   ```powershell
   wsl make -C /mnt/c/Users/jaden/OneDrive/Documents/RPI/Fall2025/AdvancedComputerSystems/Projects/TrackB benchmarks
   ```

2. **Run the Experiment 1 synthetic sweep:**

   ```powershell
   wsl bash -lc 'cd /mnt/c/Users/jaden/OneDrive/Documents/RPI/Fall2025/AdvancedComputerSystems/Projects/TrackB/experiments/Experiment1_DRAM_Baseline && ./scripts/experiment1.sh'
   ```

This regenerates all `dram_experiment1_synth_n1e5_q1e3_ef100_EF_SEARCH-*.json` files in `results/raw/`.

## How to run the SIFT1M DRAM baseline

The full SIFT1M DRAM baseline is currently run via a direct call to `bin/benchmark_recall` using the SIFT1M data that lives under `data/SIFT1M/sift/`.

**Prerequisites:**

- Dataset files present:
  - `data/SIFT1M/sift/sift_base.fvecs`
  - `data/SIFT1M/sift/sift_query.fvecs`
  - `data/SIFT1M/sift/sift_groundtruth.ivecs`
- Benchmarks built as above (so that `bin/benchmark_recall` exists).

**Command (from the project root, via WSL):**

```powershell
wsl bash -lc 'cd /mnt/c/Users/jaden/OneDrive/Documents/RPI/Fall2025/AdvancedComputerSystems/Projects/TrackB && ./bin/benchmark_recall \
  --mode dram \
  --dataset-path data/SIFT1M/sift/sift_base.fvecs \
  --dataset-name SIFT1M \
  --query-path data/SIFT1M/sift/sift_query.fvecs \
  --groundtruth-path data/SIFT1M/sift/sift_groundtruth.ivecs \
  --num-base 1000000 \
  --num-queries 10000 \
  --dim 128 \
  --k 10 \
  --M 24 \
  --ef-construction 300 \
  --ef-search 512 \
  --hnsw-build-threads 4 \
  --json-out experiments/Experiment1_DRAM_Baseline/results/raw/dram_sift1m_M24_efc300_efs512_nb1e6_q1e4_t4.json'
```

This produces a JSON log containing the tuned SIFT1M DRAM baseline (near-perfect recall, multi-threaded build, and millisecond-level latencies).

## How to analyze results

Use the provided Python analysis script to summarize and plot all JSON files in `results/raw/`:

```powershell
wsl bash -lc 'cd /mnt/c/Users/jaden/OneDrive/Documents/RPI/Fall2025/AdvancedComputerSystems/Projects/TrackB/experiments/Experiment1_DRAM_Baseline && python3 scripts/analyze_experiment1.py'
```

This script:

- Prints a tabular summary (file, dataset, mode, k, num_queries, recall, QPS, p50/p95/p99 latency).
- Generates plots in `results/plots/`:
  - `exp1_recall_qps.png` – recall@k and QPS vs configuration (e.g., vs `ef_search`).
  - `exp1_latency_percentiles.png` – p50/p95/p99 latency vs configuration.

Both the synthetic sweep and the SIFT1M baselines appear in this summary, so you can visually compare small synthetic trends with the large real-dataset result.

## Files produced by this experiment

- **Raw JSON logs:** `results/raw/*.json`
  - Synthetic: `dram_experiment1_synth_n1e5_q1e3_ef100_EF_SEARCH-*.json`
  - Early SIFT1M run (under-tuned, kept only for history): `dram_sift1m_ef256_q200.json`
  - Tuned SIFT1M DRAM baseline: `dram_sift1m_M24_efc300_efs512_nb1e6_q1e4_t4.json`
- **Plots:** `results/plots/exp1_recall_qps.png`, `results/plots/exp1_latency_percentiles.png`
- **Conclusions:** `CONCLUSIONS.md` (high-level interpretation of the results for use in the final report)

Refer to `CONCLUSIONS.md` in this directory for a concise narrative summary of what this experiment shows about DRAM-only HNSW behavior on both synthetic and SIFT1M datasets.
