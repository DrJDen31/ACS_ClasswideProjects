# Experiment 3 Conclusions: Cache Policy Comparison

This experiment compares cache replacement policies for the tiered DRAM+SSD backend used by `TieredHNSW`.
We fix the workload and cache size, then vary the cache policy between LRU and LFU.

## Setup (summary)

- Synthetic Gaussian data (same generator as Experiment 2).
- Base vectors: 20,000; query vectors: 2,000.
- Dimension: 128; `k = 10`.
- HNSW parameters: `M = 24`, `ef_construction = 300`, `ef_search = 256`, `seed = 42`.
- Tiered backend with a DRAM cache sized to hold roughly 25% of the base set.
- Policies compared:
  - LRU (`--cache-policy lru`)
  - LFU (`--cache-policy lfu`)

See `README.md` for full details on how to run the experiment and analysis scripts.

## Quantitative summary (approximate)

From the JSON logs and analysis script, we observe the following (values rounded for readability):

- **LRU policy** (`exp3_tiered_lru_nb20k_q2k_efs256.json`)
  - Recall@10: ≈ 0.998
  - Cache hit rate: ≈ 0.17
  - Effective QPS: O(10^2) (≈ 1.5e2)
  - Modeled SSD device time: O(10^6) µs
- **LFU policy** (`exp3_tiered_lfu_nb20k_q2k_efs256.json`)
  - Recall@10: ≈ 0.998 (very similar to LRU)
  - Cache hit rate: ≈ 0.26 (substantially higher than LRU)
  - Effective QPS: O(10^0)–O(10^1) (tens of times lower than LRU)
  - Modeled SSD device time: slightly lower than LRU

Both policies deliver essentially identical recall at the same `ef_search`, but differ strongly in performance and cache behavior.

## Interpretation

- **Hit rate vs throughput trade-off**

  - LFU improves the cache hit rate compared to LRU and slightly reduces modeled SSD device time.
  - Despite the better hit rate, LFU yields much worse end-to-end performance (QPS and latency) on this workload.

- **Possible reasons for LFU slowdown**

  - Our LFU implementation maintains additional metadata per access and may introduce higher per-access overhead than LRU.
  - The synthetic workload and graph traversal pattern may interact poorly with LFU (e.g., frequent revisits or bursts that favor recency more than pure frequency).
  - As a result, the benefit from increased hit rate is outweighed by policy and access-management overheads.

- **LRU vs LFU under this configuration**
  - **LRU**: lower hit rate but significantly higher QPS and lower observed latency.
  - **LFU**: higher hit rate but dramatically reduced throughput and higher latency.
  - For this particular workload, cache size, and implementation, **LRU is clearly the better choice**.

## Takeaways and future work

- A higher cache hit rate does not necessarily translate to a faster system: policy overhead and access patterns matter.
- LRU appears to be a strong default for this tiered HNSW configuration.
- LFU, at least in this simple form, is not competitive here and would likely require optimization and/or tuning.

Potential directions for follow-up experiments:

- Add and evaluate more advanced policies (e.g., ARC, two-queue, or graph/topology-aware policies).
- Vary cache capacity to see whether LFU becomes more attractive at different sizes.
- Test on different workloads (e.g., with stronger locality or different query distributions) to see where LFU might win.
- Profile the implementation to separate pure policy logic overhead from backend I/O effects.
