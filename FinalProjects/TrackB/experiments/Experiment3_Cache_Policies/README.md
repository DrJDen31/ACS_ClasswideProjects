# Experiment 3: Cache Policy Comparison

Compare cache replacement/admission policies for the tiered DRAM+SSD backend used by `TieredHNSW`.

## Goals
- Compare at least two policies (LRU and LFU) under a fixed workload and cache size.
- Measure cache hit rate, recall@k, QPS / effective QPS, and I/O stats (reads, bytes, modeled SSD device time) per policy.
- Produce plots and a short write-up that help decide which policy is preferable for this workload.

## Workload and configuration
- Synthetic Gaussian vectors (same generator and defaults as Experiment 2).
- Base set size: 20,000 vectors.
- Query set size: 2,000 vectors.
- Dimension: 128, `k = 10`.
- HNSW parameters:
  - `M = 24`
  - `ef_construction = 300`
  - `ef_search = 256`
  - `seed = 42`
- Tiered backend with a fixed DRAM cache capacity (≈ 25% of base vectors).
- Policies compared in this experiment:
  - LRU (`--cache-policy lru`)
  - LFU (`--cache-policy lfu`)

All other benchmark parameters match the defaults used in the tiered configuration of Experiment 2 so results are comparable.

## How to run the experiment

From the project root under WSL:

1. Build the benchmarks if needed:
   - `make benchmarks`
2. Run the Experiment 3 driver script:
   - `cd experiments/Experiment3_Cache_Policies`
   - `./scripts/experiment3.sh`

The driver script `scripts/run_experiment3.py` runs `bin/benchmark_recall` twice:
- Once with `--cache-policy lru`.
- Once with `--cache-policy lfu`.

Each run uses tiered mode with the configuration listed above and writes a JSON log to:
- `results/raw/exp3_tiered_lru_nb20k_q2k_efs256.json`
- `results/raw/exp3_tiered_lfu_nb20k_q2k_efs256.json`

The driver also parses the benchmark stdout to capture cache hit/miss counts and injects them into the `aggregate` section of each JSON file.

## Analysis and plots

To analyze the results and generate plots:

```bash
cd experiments/Experiment3_Cache_Policies
python3 scripts/analyze_experiment3.py
```

This script:
- Loads all `results/raw/exp3_*.json` files.
- Prints a table with, for each run:
  - Cache policy and capacity.
  - `recall_at_k`, `qps`, `effective_qps`.
  - Cache hits, misses, and derived hit rate.
  - I/O stats: number of reads, bytes read, modeled SSD device time.
- Writes plots into `results/plots/`:
  - `exp3_hit_rate_vs_policy.png` – cache hit rate vs policy.
  - `exp3_effective_qps_vs_policy.png` – effective QPS vs policy.

## High-level observations

For the default synthetic workload and cache size:
- Both LRU and LFU achieve high recall (≈ 0.998 at `k = 10`).
- LFU achieves a higher cache hit rate and slightly lower modeled SSD device time than LRU.
- However, LFU introduces a very large latency/QPS penalty in this configuration, while LRU maintains much higher QPS.

See `CONCLUSIONS.md` in this directory for a more detailed discussion of the results and their implications.
