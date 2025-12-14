# Experiment 6: Cost-Performance Trade-off

Explore cost vs performance by varying DRAM budget (cache size) for the tiered DRAM+SSD HNSW system and comparing it against both a DRAM-only baseline and an approximate ANN-in-SSD solution under a simple memory cost model.

## Goals
- Run DRAM, tiered DRAM+SSD, and ANN-in-SSD configurations on a common synthetic workload.
- Assign simple dollar costs to DRAM, baseline SSD, and hardware-level-dependent ANN-SSD capacity.
- Plot total cost vs effective QPS and identify approximate Pareto points (best cost-per-QPS trade-offs) across all three solutions.
- Additionally sweep the assumed ANN-SSD media price and visualize when Solution 3 would become cost-effective relative to DRAM/tiered baselines.

## Workload and configuration
- Synthetic Gaussian vectors (same generator and defaults as Experiments 2–5).
- Base set size: 20,000 vectors.
- Query set size: 2,000 vectors.
- Dimension: 128, `k = 10`.
- HNSW parameters:
  - `M = 24`
  - `ef_construction = 300`
  - `ef_search = 256`
  - `seed = 42`

## Modes and cache sizes

- **DRAM baseline**:
  - `mode=dram` (no SSD device model).
  - Full index in DRAM; serves as the high-throughput, high-DRAM reference.

- **Tiered HNSW (LRU)**:
  - `mode=tiered` with an NVMe-Gen3-like SSD profile:
    - `ssd_base_read_latency_us = 80.0`
    - `ssd_internal_read_bandwidth_GBps = 3.0`
    - `ssd_num_channels = 4`
    - `ssd_queue_depth = 64`
  - Cache fractions (as a fraction of `num_base`):
    - 10%, 25%, 50%, 75%, 100%  → `cache_capacity ∈ {2000, 5000, 10000, 15000, 20000}`.

- **ANN-in-SSD (Solution 3, analytic model)**:
  - `mode=ann_ssd` with the same synthetic Gaussian workload (`num_base = 20000`, `num_queries = 2000`, `dim = 128`, `k = 10`).
  - Hardware levels `L0`, `L1`, `L2`, `L3` model increasingly aggressive SSD parallelism and near-data compute as defined in `ann_in_ssd_model.cpp`.
  - Common ANN model parameters:
    - `vectors_per_block = 128`
    - `max_steps = 20`
    - `portal_degree = 2`
    - `ann-ssd-mode = cheated` so that `effective_qps` is based on an analytic combination of host time, modeled device time, and estimated compute time.

All runs use the same base/query sets and dimensionality so that `recall@10` is directly comparable, though ANN-in-SSD targets a lower recall regime.

## Cost model

In the analysis script we apply a simple, approximate memory cost model:

- Assume **4 bytes per vector dimension** (float32), so index bytes ≈ `num_vectors × dim × 4`.
- Prices (arbitrary but consistent units):
  - `DRAM_PRICE_PER_GB = 10.0`
  - Baseline tiered SSD price: `SSD_PRICE_PER_GB_TIERED = 1.0`
  - ANN-SSD price per GB depends on hardware level:
    - `L0 → $0.8/GB`, `L1 → $1.0/GB`, `L2 → $1.5/GB`, `L3 → $2.0/GB`
- DRAM / SSD usage per configuration:
  - DRAM baseline (`mode=dram`):
    - `dram_bytes = index_bytes`, `ssd_bytes = 0`.
  - Tiered (`mode=tiered`):
    - `dram_bytes ≈ cache_fraction × index_bytes`.
    - `ssd_bytes ≈ index_bytes` (full index stored on SSD backing store).
  - ANN-in-SSD (`mode=ann_ssd`):
    - Host DRAM holds only metadata and control state: `dram_bytes ≈ 0.1 × index_bytes`.
    - The full index is on the ANN-SSD: `ssd_bytes ≈ index_bytes`.
- Total cost and cost-per-QPS under the fixed price assumptions:
  - DRAM / tiered:
    - `total_cost = dram_gb * DRAM_PRICE_PER_GB + ssd_gb * SSD_PRICE_PER_GB_TIERED`.
  - ANN-in-SSD:
    - `total_cost = dram_gb * DRAM_PRICE_PER_GB + ssd_gb * price_per_GB(level)`.
  - All modes:
    - `cost_per_qps = total_cost / effective_qps`.
- Additional ANN-SSD cost sweep:
  - For each ANN hardware level, we also recompute `cost_per_qps` while sweeping an assumed ANN-SSD media price from `$0.5/GB` to `$5.0/GB` to see when Solution 3 would become competitive with the best DRAM/tiered configuration.

## How to run the experiment

From the project root under WSL:

1. Build the benchmarks if needed:
   - `make benchmarks`
2. Run the Experiment 6 driver script:
   - `cd experiments/Experiment6_Cost_Performance`
   - `./scripts/experiment6.sh`

The driver script `scripts/run_experiment6.py`:
- Runs one DRAM baseline, multiple tiered runs at cache fractions 10%, 25%, 50%, 75%, 100%, and ANN-in-SSD runs at hardware levels `L0`, `L1`, `L2`, `L3`.
- Uses the fixed NVMe-Gen3-like SSD profile for all tiered runs via:
  - `--ssd-base-latency-us`, `--ssd-internal-bw-GBps`, `--ssd-num-channels`, `--ssd-queue-depth`.
- Uses the ANN-in-SSD simulator for Solution 3 via:
  - `--mode ann_ssd`, `--dataset-name`, `--ann-ssd-mode`, `--ann-hw-level`, `--ann-vectors-per-block`, `--ann-max-steps`, `--ann-portal-degree`.
- Writes JSON logs to `results/raw/exp6_*.json`.
- Prints a quick summary of recall, QPS, and effective QPS for each configuration.

## Analysis and plots

To analyze the results and generate plots:

```bash
cd experiments/Experiment6_Cost_Performance
python3 scripts/analyze_experiment6.py
```

This script:
- Loads all `results/raw/exp6_*.json` files.
- Estimates DRAM and SSD capacity used by each configuration and applies the simple cost model.
- Prints a summary table for each run with:
  - Mode (`dram`, `tiered`, `ann_ssd`).
  - Cache fraction (for tiered), hardware level (for ANN-in-SSD).
  - Approximate DRAM GB, SSD GB, per-GB SSD price, total memory cost.
  - Effective QPS and cost-per-QPS.
- Writes plots into `results/plots/`:
  - `exp6_cost_vs_effective_qps.png` – scatter plot of total cost vs effective QPS for DRAM, tiered, and ANN-in-SSD runs, annotated with mode-specific labels (e.g., `tiered_cache=0.75`, `ann_ssd_L2`).
  - `exp6_annssd_cost_sweep.png` – line plot of `cost_per_qps` vs assumed ANN-SSD price/GB for each hardware level, with a horizontal line marking the best DRAM/tiered cost-per-QPS.

## High-level observations

On this 20k-base, 2k-query synthetic workload under the simple cost model:
- **DRAM baseline (`mode=dram`)**:
  - Uses the most DRAM (full index, ≈0.0095 GB) but no SSD.
  - Achieves high effective throughput (≈1.2e3 effective QPS) with `total_cost ≈ 0.095` and `cost_per_qps ≈ 8.0e-5`.

- **Tiered runs (`mode=tiered`)**:
  - All share the same SSD footprint (full index on SSD, ≈0.0095 GB) but differ in DRAM usage according to cache fraction.
  - Effective QPS increases with larger cache fractions (from ≈1.4e2 at 10% cache to ≈3.4e2 at 100% cache), while total cost also increases (≈0.019 → ≈0.105).
  - All tiered points have higher cost-per-QPS than the DRAM baseline in this small-scale setting (≈1.3e-4–3.1e-4 vs ≈8.0e-5), so DRAM-only remains the best choice among Solutions 1–2 here.

- **ANN-in-SSD runs (`mode=ann_ssd`, hardware levels L0–L3)**:
  - Recall is significantly lower than HNSW-based solutions (`recall@10 ≈ 0.14–0.18` vs ≈0.998), reflecting a more approximate search regime.
  - Under the fixed per-level ANN-SSD prices, the very high modeled `effective_qps` for levels `L1`–`L3` yields much lower cost-per-QPS than any DRAM or tiered configuration.
    - Example (approximate):
      - L0: `total_cost ≈ 0.017`, `effective_qps ≈ 3.8e2`, `cost_per_qps ≈ 4.5e-5`.
      - L1: `total_cost ≈ 0.019`, `effective_qps ≈ 1.5e3`, `cost_per_qps ≈ 1.3e-5`.
      - L2/L3: `total_cost ≈ 0.024–0.029` with `effective_qps` in the `7.5e4–2.2e5` range, giving extremely small cost-per-QPS under the analytic model.
  - The additional `exp6_annssd_cost_sweep.png` plot sweeps ANN-SSD media price from `$0.5/GB` to `$5.0/GB`:
    - L0 crosses the best DRAM/tiered cost-per-QPS line around ≈`$2/GB`; below that, L0 is more cost-effective than any DRAM/tiered point, above that it becomes worse.
    - L1–L3 remain below the best DRAM/tiered cost-per-QPS line across the entire 0.5–5 $/GB sweep due to their very high modeled throughput.

These results should be read as a **methodology demonstration** rather than a realistic claim about absolute cost/performance of ANN-in-SSD: the ANN model uses a "cheated" analytic effective QPS and operates at much lower recall than HNSW. See `CONCLUSIONS.md` in this directory for a more detailed discussion of these trade-offs and caveats.
