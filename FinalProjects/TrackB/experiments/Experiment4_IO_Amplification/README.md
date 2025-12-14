# Experiment 4: I/O Amplification Analysis

Quantify how I/O per query (reads, bytes, modeled device time) changes as we vary the tiered cache size, and compare against a DRAM baseline.

## Goals
- Measure I/Os per query vs cache size for the tiered DRAM+SSD HNSW system.
- Keep the HNSW configuration and workload fixed so that recall remains high and comparable.
- Compare tiered runs to a DRAM run as a zero-I/O reference.

## Workload and configuration
- Synthetic Gaussian vectors (same generator and defaults as Experiments 2 and 3).
- Base set size: 20,000 vectors.
- Query set size: 2,000 vectors.
- Dimension: 128, `k = 10`.
- HNSW parameters:
  - `M = 24`
  - `ef_construction = 300`
  - `ef_search = 256`
  - `seed = 42`
- Tiered backend:
  - DRAM cache fronting a backing store with IOStats + modeled SSD device time.
  - LRU cache policy.

## Cache sizes and runs

We sweep the tiered cache capacity as a fraction of `num_base` while keeping everything else fixed:

- DRAM baseline:
  - `mode=dram` (no SSD I/O, serves as a reference).
- Tiered runs (`mode=tiered`, LRU policy):
  - Cache fractions: 5%, 10%, 25%, 50%, 100% of `num_base`.
  - For `num_base = 20,000`, this corresponds to capacities `{1000, 2000, 5000, 10000, 20000}`.

All runs use the same HNSW parameters and workload so that recall@10 is directly comparable.

## How to run the experiment

From the project root under WSL:

1. Build the benchmarks if needed:
   - `make benchmarks`
2. Run the Experiment 4 driver script:
   - `cd experiments/Experiment4_IO_Amplification`
   - `./scripts/experiment4.sh`

The driver script `scripts/run_experiment4.py`:
- Runs one DRAM baseline and multiple tiered runs at different cache fractions.
- Writes JSON logs to `results/raw/exp4_*.json`.
- Prints a quick summary of recall, QPS, and I/O per query for each configuration.

## Analysis and plots

To analyze the results and generate plots:

```bash
cd experiments/Experiment4_IO_Amplification
python3 scripts/analyze_experiment4.py
```

This script:
- Loads all `results/raw/exp4_*.json` files.
- Prints a summary table with, for each run:
  - Mode (`dram` vs `tiered`).
  - Cache capacity and derived cache fraction (capacity / num_vectors).
  - `recall_at_k`, `qps`, `effective_qps`.
  - I/O per query: reads/query, bytes/query, modeled device_time_us per query.
- Writes plots into `results/plots/`:
  - `exp4_reads_per_query_vs_cache_frac.png` – reads/query vs cache fraction (tiered only).
  - `exp4_bytes_per_query_vs_cache_frac.png` – bytes/query vs cache fraction.
  - `exp4_device_time_per_query_vs_cache_frac.png` – modeled device time/query vs cache fraction (when available).

## High-level observations

On the 20k-base, 2k-query synthetic workload with LRU tiered caching:
- Recall@10 remains ≈0.998 for all cache sizes and for the DRAM baseline.
- As cache fraction increases from 5–10% up to 50% and 100%, I/O per query drops significantly:
  - Roughly 7k reads/query at 5–10% cache.
  - ≈6.1k reads/query at 25% cache.
  - ≈2.9k reads/query at 50% cache.
  - 0 reads/query at 100% cache (cache fits the working set).
- Modeled SSD device time per query follows the same trend, decreasing as cache size grows and reaching 0 when the cache holds the entire dataset.
- DRAM (`mode=dram`) provides a zero-I/O reference with higher QPS; tiered runs incur additional overhead from the tiering machinery even when the cache is large.

See `CONCLUSIONS.md` in this directory for a more detailed discussion of these trends and their implications for I/O amplification.
