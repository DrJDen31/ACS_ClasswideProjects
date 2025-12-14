# Experiment 7 Conclusions: Scaling

## Setup (summary)

This experiment measures scaling behavior as dataset size grows, focusing on how build time and throughput change with `num_base`.

- Dataset: SIFT1M
  - Base: `data/SIFT1M/sift/sift_base.fvecs`
  - Queries: `data/SIFT1M/sift/sift_query.fvecs`
  - Ground truth: `data/SIFT1M/sift/sift_groundtruth.ivecs`
- Runs used `num_queries = 2000`, `dim = 128`, `k = 10`.
- HNSW parameters: `M=24`, `ef_construction=300`, `ef_search=512`, `hnsw_build_threads=8`.
- Tiered parameters: `cache_frac = 0.25` (25%), LRU, with an NVMe Gen3-like SSD model (`80us`, `3GB/s`, `4ch`, `QD=64`).

## Quantitative snapshot

From `scripts/analyze_experiment7.py`:

- DRAM (`mode=dram`):
  - 20k: build ≈ 2.81s, effective QPS ≈ 1524.97, recall@10 ≈ 0.228
  - 100k: build ≈ 27.75s, effective QPS ≈ 669.42, recall@10 ≈ 0.849
  - 500k: build ≈ 280.40s, effective QPS ≈ 395.79, recall@10 ≈ 0.998
  - 1M: build ≈ 642.04s, effective QPS ≈ 332.25, recall@10 ≈ 0.999

- Tiered (`mode=tiered`, 25% cache):
  - 20k: build ≈ 3.17s, effective QPS ≈ 242.53, recall@10 ≈ 0.228
  - 100k: build ≈ 29.55s, effective QPS ≈ 112.48, recall@10 ≈ 0.849
  - 500k: build ≈ 271.38s, effective QPS ≈ 54.79, recall@10 ≈ 0.999

## Interpretation

- **Build time scaling**
  - Build time grows rapidly with `num_base` for both DRAM and tiered, reaching ~10 minutes at 1M (DRAM) under these parameters.
  - Tiered build times are similar to DRAM at larger scales (e.g., 500k), since build is mostly host-side graph construction and vector ingestion.

- **Throughput scaling**
  - Effective QPS decreases as `num_base` grows in both modes.
  - Tiered is consistently slower than DRAM here due to cache misses and modeled device time.

- **Recall caveat for subset runs**
  - The SIFT ground-truth file corresponds to the full 1M base. When running with `num_base < 1M`, ground-truth neighbor IDs outside the subset are filtered, which can make the reported `recall@10` for small subsets appear artificially low. This is visible at 20k and (to a lesser extent) 100k.

## Takeaways

- At 1M scale, DRAM HNSW delivers high recall (~0.999) but has substantial build time (~642s with 8 build threads) and moderate throughput (~332 effective QPS for 2k queries).
- Tiered at 25% cache shows similar recall at larger `num_base` but significantly lower effective QPS (e.g., ~55 at 500k) under this SSD model.
- For cleaner recall-vs-scale conclusions on subsets, Experiment 7 should be extended to recompute ground truth per subset (or use consistent subset ground truth files).
