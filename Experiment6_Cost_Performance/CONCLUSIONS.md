# Experiment 6 Conclusions: Cost-Performance Trade-off

This experiment explores how DRAM budget (cache size) and SSD usage interact under a simple memory cost model, comparing DRAM-only, tiered DRAM+SSD, and an analytic ANN-in-SSD solution on a fixed synthetic workload.

## Setup (summary)

- Synthetic Gaussian data: 20,000 base vectors, 2,000 queries, 128D, `k = 10`.
- HNSW parameters: `M = 24`, `ef_construction = 300`, `ef_search = 256`, `seed = 42`.
- Configurations:

  - **DRAM baseline** (`exp6_dram_nb20k_q2k_efs256`): `mode=dram`, full index in DRAM.
  - **Tiered HNSW (LRU)** (`mode=tiered`) with an NVMe-Gen3-like SSD model:
    - `ssd_base_read_latency_us = 80.0`, `ssd_internal_read_bandwidth_GBps = 3.0`.
    - `ssd_num_channels = 4`, `ssd_queue_depth = 64`.
    - Cache fractions: 10%, 25%, 50%, 75%, 100% of `num_base`.
  - **ANN-in-SSD (Solution 3)** (`mode=ann_ssd`, levels `L0`, `L1`, `L2`, `L3`):
    - Same synthetic workload (20k/2k, 128D, `k = 10`).
    - Blocked layout (`vectors_per_block = 128`), `max_steps = 20`, `portal_degree = 2`.
    - Uses the analytic "cheated" mode to estimate `effective_qps` from search time, modeled device time, and estimated compute time.

- Cost model (approximate, for relative comparisons only):
  - Index bytes ≈ `num_vectors × dim × 4` (float32).
  - DRAM price: `$10/GB`.
  - Baseline tiered SSD price: `$1/GB`.
  - ANN-SSD SSD price is hardware-level-dependent:
    - `L0 → $0.8/GB`, `L1 → $1.0/GB`, `L2 → $1.5/GB`, `L3 → $2.0/GB`.
  - DRAM/SSD usage:
    - DRAM baseline: DRAM holds full index; SSD not used.
    - Tiered: DRAM holds `cache_fraction × index_bytes`; SSD holds full index.
    - ANN-in-SSD: DRAM holds metadata and control (modeled as `0.1 × index_bytes`); SSD holds full index.
  - Derived metrics (per configuration):
    - `total_cost = dram_gb * 10 + ssd_gb * price_per_GB(mode, level)`.
    - `cost_per_qps = total_cost / effective_qps`.

## Quantitative snapshot (approximate)

From the Experiment 6 summary (rounded):

- **DRAM baseline (`mode=dram`)**

  - `dram_gb ≈ 0.0095`, `ssd_gb = 0.0` → `total_cost ≈ 0.095`.
  - `effective_qps ≈ 1.20e3`.
  - `cost_per_qps ≈ 8.0e-5`.

- **Tiered HNSW (`mode=tiered`, 10–100% cache)**

  - All tiered configurations use `ssd_gb ≈ 0.0095` (full index on SSD) and vary DRAM from ≈0.0010 GB (10% cache) to ≈0.0095 GB (100% cache).
  - Example points:
    - 10% cache (`cache=2000`): `total_cost ≈ 0.019`, `effective_qps ≈ 1.43e2`, `cost_per_qps ≈ 1.3e-4`.
    - 50% cache (`cache=10000`): `total_cost ≈ 0.057`, `effective_qps ≈ 1.94e2`, `cost_per_qps ≈ 2.9e-4`.
    - 75% cache (`cache=15000`): `total_cost ≈ 0.081`, `effective_qps ≈ 2.82e2`, `cost_per_qps ≈ 2.9e-4`.
    - 100% cache (`cache=20000`): `total_cost ≈ 0.105`, `effective_qps ≈ 3.43e2`, `cost_per_qps ≈ 3.1e-4`.
  - All tiered points have higher cost-per-QPS than the DRAM baseline in this small synthetic setting.

- **ANN-in-SSD (`mode=ann_ssd`, L0–L3)**

  - All ANN-SSD levels use `dram_gb ≈ 0.0010` and `ssd_gb ≈ 0.0095` (full index on SSD, small DRAM metadata footprint).
  - Under the fixed per-level SSD prices, we observe:
    - L0: `total_cost ≈ 0.017`, `effective_qps ≈ 3.81e2`, `cost_per_qps ≈ 4.5e-5`.
    - L1: `total_cost ≈ 0.019`, `effective_qps ≈ 1.52e3`, `cost_per_qps ≈ 1.3e-5`.
    - L2: `total_cost ≈ 0.024`, `effective_qps ≈ 7.53e4`, `cost_per_qps ≈ 3.1e-7`.
    - L3: `total_cost ≈ 0.029`, `effective_qps ≈ 2.23e5`, `cost_per_qps ≈ 1.3e-7`.
  - These extremely low cost-per-QPS numbers for L2/L3 come from the analytic model combining very small estimated search/compute/device times with modest media cost.

_(All costs are in arbitrary units based on the simple DRAM/SSD price assumptions and an analytic ANN-SSD model.)_

## Interpretation

### Recall vs cost/performance trade-offs

- **Recall behavior**

  - DRAM and tiered HNSW runs maintain high-quality search: `recall@10 ≈ 0.998` across all cache sizes.
  - ANN-in-SSD runs operate in a lower-recall regime: `recall@10 ≈ 0.14–0.18` for L0–L3 in this configuration.
  - Any comparison of cost-per-QPS should be read with this quality gap in mind: ANN-in-SSD here trades substantial recall for throughput.

- **Cost vs effective QPS for DRAM and tiered**

  - DRAM baseline remains the **cheapest per unit of throughput** among Solutions 1–2:
    - High `effective_qps` (≈1.2e3) with only ≈0.0095 GB of DRAM and no SSD.
    - All tiered runs have lower effective QPS (≈1.4e2–3.4e2) and pay extra SSD cost, so their `cost_per_qps` is worse (≈1.3e-4–3.1e-4).
  - Within tiered runs, increasing cache size moves along a cost/QPS frontier:
    - 10% cache is cheapest in absolute cost but also slowest.
    - 75–100% cache improve QPS but increase total cost; none surpass the DRAM baseline on cost-per-QPS at this scale.

### ANN-in-SSD cost sweep vs DRAM/tiered baselines

- Under the **fixed** ANN-SSD per-level prices, the analytic model makes levels `L1`–`L3` appear dramatically more cost-effective than DRAM or tiered:
  - Even with higher SSD $/GB, the huge modeled `effective_qps` at L2/L3 drives `cost_per_qps` down to `1e-7–1e-6`, far below the DRAM baseline.
- To better understand when this would be realistic, we introduced an **ANN-SSD price sweep**:
  - For each ANN level, we recompute `cost_per_qps` while sweeping ANN-SSD media price from `$0.5/GB` to `$5.0/GB`.
  - We overlay a horizontal line at the **best DRAM/tiered `cost_per_qps`** under the fixed pricing assumptions.
  - Qualitatively:
    - L0 crosses this baseline line around ≈`$2/GB`; below that, even the weakest ANN-SSD level can be more cost-effective than any DRAM/tiered configuration.
    - L1–L3 remain below the DRAM/tiered baseline line across the entire 0.5–5 $/GB sweep, due to their very high modeled throughput.

This sweep effectively answers: *"For a given hardware level, how expensive can the ANN-SSD media become before it loses its cost-per-QPS advantage over conventional DRAM/tiered setups?"*

## Takeaways

- Under this small synthetic workload and simple pricing:
  - **Solution 1 (DRAM-only)** is still the best option if you require high recall and the index fits comfortably in DRAM.
  - **Solution 2 (tiered HNSW)** provides a range of DRAM/SSD mixes but does not beat DRAM on cost-per-QPS here; it mainly illustrates how cost and QPS move as you change cache fraction.
  - **Solution 3 (ANN-in-SSD)**, as modeled here, can be *much* more cost-effective in terms of cost-per-QPS, but only by operating at substantially lower recall and relying on an optimistic analytic model of near-data compute.
- The additional ANN-SSD price-sweep plot (`exp6_annssd_cost_sweep.png`) shows that even if ANN-SSD media were substantially more expensive than baseline SSDs, higher-end hardware levels (L1–L3) would still be cost-competitive in this model, while L0 requires more aggressive pricing to overtake DRAM/tiered.
- Interpreting these results quantitatively in a real system would require:
  - More realistic modeling of near-data compute capabilities and queueing.
  - Matching recall targets across solutions (e.g., tuning ANN-SSD parameters to reach `recall@10 ≈ 0.95–0.99`).
  - Incorporating larger datasets and platform constraints where DRAM-only becomes impractical.

## Future directions

- Extend the cost model to larger synthetic or real datasets (e.g., SIFT1M) where DRAM capacity is non-trivial and SSD-based designs become more attractive.
- Calibrate the ANN-in-SSD model to target specific recall/QPS targets and compare more directly against HNSW.
- Incorporate build time and energy or TCO considerations into the cost side of the analysis.
- Combine this cost-performance view with SSD sensitivity (Experiment 5), cache policy/size studies (Experiments 3–4), and cross-solution comparisons (Experiment 9) for a more holistic picture of when tiered DRAM+SSD and ANN-in-SSD architectures are compelling relative to DRAM-only baselines.
