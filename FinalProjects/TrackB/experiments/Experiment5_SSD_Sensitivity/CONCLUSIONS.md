# Experiment 5 Conclusions: SSD Sensitivity

This experiment studies how SSD characteristics in the `SsdSimulator` impact modeled device time and throughput for the tiered DRAM+SSD HNSW system, using a fixed HNSW configuration and workload, and compares those tiered runs against a DRAM baseline.

## Setup (summary)

- Synthetic Gaussian data (same as Experiments 2–4).
- Base vectors: 20,000; query vectors: 2,000.
- Dimension: 128; `k = 10`.
- HNSW parameters: `M = 24`, `ef_construction = 300`, `ef_search = 256`, `seed = 42`.
- Configurations:
  - DRAM baseline: `mode=dram` (no SSD device model, zero device_time_us by definition).
  - Tiered HNSW: `mode=tiered`, LRU cache, cache capacity fixed at 50% of base (`cache_capacity = 10000`).
  - SSD simulator parameters varied across four profiles via new CLI flags:
    - `--ssd-base-latency-us`
    - `--ssd-internal-bw-GBps`
    - `--ssd-num-channels`
    - `--ssd-queue-depth`

## Quantitative snapshot (approximate)

From the Experiment 5 summary (rounded):

- **DRAM baseline (`exp5_dram_nb20k_q2k_efs256`)**

  - Recall@10: ≈ 0.99785
  - Device time/query: 0 µs (no SSD)
  - Effective QPS: ≈ 1.5e3

- **Tiered, SATA-like SSD (`exp5_tiered_sata_like_nb20k_q2k_efs256`)**

  - SSD parameters: ~100 µs base latency, 0.5 GB/s, 2 channels × 32 queue depth.
  - Recall@10: ≈ 0.99785
  - Modeled device time/query: ≈ 4.5 ms
  - Effective QPS: ≈ 1.2e2

- **Tiered, NVMe Gen3-like SSD (`exp5_tiered_nvme_gen3_nb20k_q2k_efs256`)**

  - SSD parameters: ~80 µs, 3 GB/s, 4 channels × 64 queue depth.
  - Recall@10: ≈ 0.99785
  - Device time/query: ≈ 0.9 ms
  - Effective QPS: ≈ 2.0e2

- **Tiered, NVMe fast SSD (`exp5_tiered_nvme_fast_nb20k_q2k_efs256`)**

  - SSD parameters: ~40 µs, 6 GB/s, 8 channels × 64 queue depth.
  - Recall@10: ≈ 0.99785
  - Device time/query: ≈ 0.22 ms
  - Effective QPS: ≈ 2.3e2

- **Tiered, NVMe ultra SSD (`exp5_tiered_nvme_ultra_nb20k_q2k_efs256`)**
  - SSD parameters: ~20 µs, 8 GB/s, 16 channels × 128 queue depth.
  - Recall@10: ≈ 0.99785
  - Device time/query: ≈ 0.03 ms
  - Effective QPS: ≈ 2.4e2

## Interpretation

- **Recall stability across SSD profiles**

  - Recall@10 remains ≈0.998 for DRAM and all tiered runs, as expected, since HNSW parameters and search logic are unchanged; only the modeled storage device characteristics differ.

- **Strong dependence of device time on SSD parameters**

  - Moving from SATA-like to NVMe-like profiles dramatically reduces modeled device time per query:
    - From ~4.5 ms/query (SATA-like) down to sub-millisecond and then tens of microseconds per query.
  - This confirms that, under the simulator’s assumptions, higher bandwidth, more channels, and lower base latency translate directly into less time spent at the SSD per query.

- **Throughput vs SSD speed: diminishing returns**

  - Effective QPS improves as the SSD gets faster (SATA-like → NVMe Gen3 → NVMe fast → NVMe ultra), but the gains are sublinear relative to the reductions in device time:
    - Large device-time reductions from SATA-like to NVMe Gen3 yield a noticeable jump in effective QPS.
    - Further improvements (NVMe fast → ultra) slightly increase effective QPS but do not approach the DRAM-only baseline.
  - This behavior indicates that beyond a certain point, **host compute and tiering overheads** dominate; the SSD is no longer the primary bottleneck.

- **Gap to DRAM baseline**
  - The DRAM baseline achieves an order-of-magnitude higher effective QPS (~1.5e3) than all tiered configurations because it has zero modeled device time and no tiered storage indirection.
  - Even with a very fast SSD and a 50% cache, tiered runs remain compute- and overhead-limited, showing that removing I/O alone is not enough to match a pure DRAM design.

## Takeaways

- SSD parameters have a **first-order effect** on modeled device time per query and a clear, though eventually saturating, impact on effective QPS for the tiered system.
- There is a point of **diminishing returns** where further SSD improvements yield relatively small end-to-end throughput gains because other components (CPU, tiering logic) become the bottleneck.
- The DRAM baseline still sets a much higher throughput ceiling; tiered designs must either accept that gap or combine fast SSDs with additional optimizations (multi-threaded search, smarter caching, layout, etc.) to close it.

## Future directions

- Explore SSD sensitivity at different cache sizes (e.g., 10–25% vs 50%) to see how the interaction between cache size and SSD speed affects I/O and QPS.
- Combine SSD sweeps with cache-policy variations (Experiment 3) to understand which policies are more robust under slower vs faster SSDs.
- Use these sensitivity curves to motivate realistic SSD parameter choices for larger-scale experiments (e.g., SIFT1M) and for ANN-in-SSD simulations.
