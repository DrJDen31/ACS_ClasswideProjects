# Experiment 2 Conclusions: Tiered vs DRAM

## What this experiment measured

- **Goal:** Compare **pure DRAM HNSW** against **Tiered HNSW** (DRAM cache + SSD simulator) on a common synthetic workload.
- **Dataset:** Synthetic Gaussian, `num_base = 20,000`, `num_queries = 2,000`, `dim = 128`, `k = 10`.
- **HNSW parameters:** `M = 24`, `ef_construction = 300`, `ef_search = 256`, `seed = 42`.
- **Modes:**
  - `mode = dram` (DRAM-only baseline).
  - `mode = tiered` with cache capacities of 10%, 25%, 50%, and 100% of the index (by vector count).

Results are logged as `results/raw/exp2_*.json`.

## DRAM baseline (exp2_dram_nb20k_q2k_efs256)

From `exp2_dram_nb20k_q2k_efs256.json`:

- `recall@10 ≈ 0.99785` (essentially perfect for this synthetic task).
- `build_time_s ≈ 33.6 s` for 20k base vectors.
- `search_time_s ≈ 1.34 s` for 2,000 queries.
- `qps ≈ 57.2` (queries per second over build+search).
- `effective_qps ≈ 1,495` (search-only QPS; no device time in DRAM mode).
- Latencies: p50/p95/p99 ≈ 0.62 / 0.90 / 1.16 ms.
- I/O stats: `num_reads = 0`, `bytes_read = 0`, `device_time_us = 0` (as expected for pure DRAM).

This serves as the **reference point** for how fast HNSW can be when everything lives in DRAM and there is no I/O cost.

## Tiered runs (exp2_tiered_cache{10,25,50,100}\_nb20k_q2k_efs256)

Each tiered run uses the same HNSW parameters and synthetic dataset, differing only in `cache_capacity`.

From the JSON logs:

- **Recall:**

  - All tiered runs have `recall@10 ≈ 0.99785`, **matching the DRAM baseline**.
  - This indicates that introducing the tiered backend does not harm recall for this configuration.

- **Host-level QPS and times:** (approximate)

  - `cache10` (10% cache):
    - `build_time_s ≈ 33.1 s`, `search_time_s ≈ 8.87 s`.
    - `qps ≈ 47.6` (build+search).
  - `cache25` (25% cache):
    - `build_time_s ≈ 35.1 s`, `search_time_s ≈ 11.2 s`.
    - `qps ≈ 43.1`.
  - `cache50` (50% cache):
    - `build_time_s ≈ 33.6 s`, `search_time_s ≈ 8.65 s`.
    - `qps ≈ 47.3`.
  - `cache100` (100% cache):
    - `build_time_s ≈ 33.4 s`, `search_time_s ≈ 5.79 s`.
    - `qps ≈ 51.1`.

  **Observation:** Host-level throughput (`qps`) is in the same order of magnitude across runs, but tiered runs have substantially higher measured per-query latency even before adding modeled device time (due to tiering/cache bookkeeping).

- **Effective QPS (search + device time):**

  - DRAM baseline: `effective_qps ≈ 1,495` (no device time, so this is just search-only QPS).
  - Tiered runs:
    - `cache10`: `effective_qps ≈ 151`.
    - `cache25`: `effective_qps ≈ 133`.
    - `cache50`: `effective_qps ≈ 192`.
    - `cache100`: `effective_qps ≈ 346`.

  **Interpretation:**

  - Once modeled SSD **device time** is included, the effective throughput of the tiered system drops by roughly **4×–11×** compared to the DRAM baseline, depending on cache size.
  - Larger caches reduce SSD reads and device time, pushing tiered effective QPS upward (cache10 → cache100), but even with cache100 (no SSD reads) the tiered path remains slower than DRAM due to additional tiering/cache overhead.

- **I/O stats and device time (cache-size effect):**

  Cache size meaningfully changes I/O volume and modeled SSD time:

  - `cache10` (10%): `num_reads ≈ 13.9M`, `bytes_read ≈ 7.12GB`, `device_time_us ≈ 4.35e6`.
  - `cache25` (25%): `num_reads ≈ 12.1M`, `bytes_read ≈ 6.21GB`, `device_time_us ≈ 3.80e6`.
  - `cache50` (50%): `num_reads ≈ 5.72M`, `bytes_read ≈ 2.93GB`, `device_time_us ≈ 1.79e6`.
  - `cache100` (100%): `num_reads = 0`, `bytes_read = 0`, `device_time_us = 0`.

  This matches the expected behavior: larger DRAM caches avoid backing-store reads and reduce SSD time.

## Conclusions and how to present this in the report

1. **Tiered vs DRAM (with caching):**

   - When the tiered backend is configured with the current `TieredBackend + SsdSimulator` setup, we observe:
     - **Same recall** as DRAM.
     - **Higher latency** in the tiered path.
     - **Lower effective QPS** once SSD device time is included, especially at smaller cache sizes.
   - This shows the cost of adding a storage tier: even if recall is preserved, SSD-like I/O time and tiering overhead can dominate throughput.

2. **Cache size strongly affects I/O and effective throughput:**

   - As cache capacity increases, `num_reads`, `bytes_read`, and modeled `device_time_us` all decrease substantially.
   - This pushes tiered `effective_qps` upward (cache10 → cache100).
   - However, even at cache100 (no SSD reads), tiered `effective_qps` remains below DRAM, showing that tiering/caching machinery adds measurable CPU-side overhead.

3. **Tiered caching improves SSD-I/O costs but does not eliminate the tiering gap:**

   - Smaller caches still incur **millions of reads** and multiple GiB of I/O over the 2,000-query batch, with modeled SSD time in the multi-second range.
   - Larger caches reduce this dramatically, but the tiered implementation remains slower than a pure DRAM implementation even when SSD I/O is eliminated.
   - This supports the core thesis of Topic 2: **I/O must be treated as a first-class design dimension**, and storage-tiering overheads must be engineered carefully to preserve DRAM-like performance.

4. **Recommended narrative in the final report:**

   - Present Experiment 2 as an **initial, synthetic Tiered vs DRAM comparison** that:
     - Confirms that tiering can preserve DRAM recall.
     - Highlights the latency and throughput penalties when SSD device time is accounted for.
   - Emphasize the cache-size trade-off:
     - Larger caches reduce I/O amplification and modeled device time, improving effective throughput.
     - Even with a very large cache, tiering overhead can still reduce throughput, motivating additional engineering (e.g., lower-overhead cache, batching, async I/O, graph/layout optimizations).

These points can be copied into the report’s Experiment 2 section, with supporting plots from `exp2_recall_effective_qps.png` and `exp2_io_per_query_vs_cache.png` to visually reinforce the observations.
