# Experiment 4 Conclusions: I/O Amplification vs Cache Size

This experiment measures how I/O per query changes as we vary the DRAM cache size in the tiered DRAM+SSD HNSW system, and compares these tiered runs against a DRAM baseline.

## Setup (summary)

- Synthetic Gaussian data (same generator as Experiments 2 and 3).
- Base vectors: 20,000; query vectors: 2,000.
- Dimension: 128; `k = 10`.
- HNSW parameters: `M = 24`, `ef_construction = 300`, `ef_search = 256`, `seed = 42`.
- Policies/configurations:
  - DRAM baseline: `mode=dram` (no SSD I/O).
  - Tiered HNSW: `mode=tiered`, LRU cache policy, IOStats + modeled SSD `device_time_us`.
- Tiered cache fractions (relative to `num_base`):
  - 5%, 10%, 25%, 50%, 100% → capacities `{1000, 2000, 5000, 10000, 20000}`.

## Quantitative summary (approximate)

From the Experiment 4 analysis output (rounded):

- **DRAM baseline (`exp4_dram_nb20k_q2k_efs256`)**

  - Recall@10: ≈ 0.99785
  - Reads/query: 0
  - Bytes/query: 0
  - Modeled device time/query: 0 µs
  - QPS: highest among all runs (no tiering overhead, no SSD I/O).

- **Tiered, 5–10% cache (`exp4_tiered_cache5`, `exp4_tiered_cache10`)**

  - Recall@10: ≈ 0.99785
  - Reads/query: ≈ 7.1k (5%) and ≈ 7.0k (10%).
  - Bytes/query: ≈ 3.6–3.7 MB.
  - Modeled device time/query: ≈ 2.2 ms.
  - QPS: slightly lower than DRAM but still in the same order of magnitude.

- **Tiered, 25% cache (`exp4_tiered_cache25`)**

  - Recall@10: ≈ 0.99785
  - Reads/query: ≈ 6.1k.
  - Bytes/query: ≈ 3.1 MB.
  - Modeled device time/query: ≈ 1.9 ms.

- **Tiered, 50% cache (`exp4_tiered_cache50`)**

  - Recall@10: ≈ 0.99785
  - Reads/query: ≈ 2.9k.
  - Bytes/query: ≈ 1.5 MB.
  - Modeled device time/query: ≈ 0.9 ms.

- **Tiered, 100% cache (`exp4_tiered_cache100`)**
  - Recall@10: ≈ 0.99785
  - Reads/query: 0 (cache holds the entire working set).
  - Bytes/query: 0.
  - Modeled device time/query: 0 µs.
  - QPS: improved relative to small-cache tiered runs but still somewhat below the pure DRAM baseline due to tiering overhead.

## Interpretation

- **Recall stability**

  - Across DRAM and all tiered cache sizes, recall@10 remains essentially constant (≈0.998). This is expected because HNSW parameters and traversal logic are unchanged; only where vectors are stored (DRAM vs SSD) and how often they are fetched from SSD differ.

- **I/O amplification vs cache size**

  - I/O per query (reads and bytes) drops sharply as cache capacity increases:
    - At 5–10% cache, each query triggers ~7k SSD reads and ~3.6 MB of data.
    - At 25% cache, reads drop modestly.
    - At 50% cache, they drop dramatically to ~2.9k reads and ~1.5 MB per query.
    - At 100% cache, SSD reads go to zero because the DRAM cache holds the entire working set.
  - Modeled SSD device time per query tracks this trend closely, confirming that I/O amplification is dominated by cache size in this configuration.

- **Performance trade-offs**
  - Even when I/O is zero (100% tiered cache), tiered runs do not quite match DRAM QPS, reflecting overhead from the tiered backend and cache machinery.
  - For small to medium caches, the extra latency from SSD I/O (1–2+ ms per query) is visible in the modeled device time and contributes to lower effective QPS relative to the DRAM baseline.

## Takeaways

- Cache size is a **primary driver** of I/O amplification in the current tiered design: larger caches substantially reduce bytes/query and modeled device time without hurting recall.
- There is an inherent **overhead to tiering**: even with a cache that holds the full working set (100%), the tiered path is slower than a pure DRAM run because of additional indirection and bookkeeping.
- For this synthetic workload, a cache fraction around 50% already yields a substantial reduction in I/O relative to 5–10% cache, while keeping recall unchanged.

## Future directions

- Implement and evaluate I/O optimizations such as prefetching and graph layout/reordering to further reduce I/O amplification at smaller cache sizes.
- Extend this analysis to real datasets (e.g., SIFT) and larger base sizes to see whether the observed trends hold at higher scales.
- Combine these results with cache-policy experiments (Experiment 3) to understand how **policy choice** and **cache size** jointly shape I/O amplification and QPS.
