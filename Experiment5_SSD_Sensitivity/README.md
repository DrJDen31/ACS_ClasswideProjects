# Experiment 5: SSD Sensitivity

Explore how modeled SSD characteristics (latency, bandwidth, channels, queue depth) affect device time and throughput for the tiered DRAM+SSD HNSW system, and compare against a DRAM baseline.

## Goals
- Sweep SSD simulator parameters for the tiered configuration while keeping the HNSW graph and workload fixed.
- Measure how modeled `device_time_us` per query and effective QPS change across SSD profiles.
- Use a DRAM run (`mode=dram`) as a zero-device-time reference.

## Workload and configuration
- Synthetic Gaussian vectors (same generator and defaults as Experiments 2–4).
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
  - Cache capacity fixed at 50% of the base set (`cache_capacity = 10000` for `num_base = 20000`).

## SSD profiles

We vary the `SsdSimulator` device config via new CLI flags to approximate a spectrum from slow SATA-like to aggressive NVMe-like devices. The profiles used in this experiment are:

- `sata_like`:
  - `ssd_base_read_latency_us = 100.0`
  - `ssd_internal_read_bandwidth_GBps = 0.5`
  - `ssd_num_channels = 2`
  - `ssd_queue_depth_per_channel = 32`
- `nvme_gen3`:
  - `ssd_base_read_latency_us = 80.0`
  - `ssd_internal_read_bandwidth_GBps = 3.0`
  - `ssd_num_channels = 4`
  - `ssd_queue_depth_per_channel = 64`
- `nvme_fast`:
  - `ssd_base_read_latency_us = 40.0`
  - `ssd_internal_read_bandwidth_GBps = 6.0`
  - `ssd_num_channels = 8`
  - `ssd_queue_depth_per_channel = 64`
- `nvme_ultra`:
  - `ssd_base_read_latency_us = 20.0`
  - `ssd_internal_read_bandwidth_GBps = 8.0`
  - `ssd_num_channels = 16`
  - `ssd_queue_depth_per_channel = 128`

We also include a DRAM baseline (`mode=dram`) on the same workload with no SSD device model attached.

## How to run the experiment

From the project root under WSL:

1. Build the benchmarks if needed:
   - `make benchmarks`
2. Run the Experiment 5 driver script:
   - `cd experiments/Experiment5_SSD_Sensitivity`
   - `./scripts/experiment5.sh`

The driver script `scripts/run_experiment5.py`:
- Runs one DRAM baseline and four tiered runs (one per SSD profile) on the same 20k/2k synthetic workload.
- For tiered runs, sets `--cache-capacity` to 50% of `num_base` and passes the SSD parameters via:
  - `--ssd-base-latency-us`
  - `--ssd-internal-bw-GBps`
  - `--ssd-num-channels`
  - `--ssd-queue-depth`
- Writes JSON logs to `results/raw/exp5_*.json`.
- Prints a quick summary including recall, QPS, effective QPS, and modeled device time per query for each configuration.

## Analysis and plots

To analyze the results and generate plots:

```bash
cd experiments/Experiment5_SSD_Sensitivity
python3 scripts/analyze_experiment5.py
```

This script:
- Loads all `results/raw/exp5_*.json` files.
- Prints a summary table with, for each run:
  - Mode (`dram` vs `tiered`).
  - SSD parameters (latency, bandwidth, channels, queue depth).
  - `recall_at_k`, `qps`, `effective_qps`.
  - Modeled `device_time_us` per query.
- Writes plots into `results/plots/`:
  - `exp5_effective_qps_vs_ssd_profile.png` – effective QPS vs SSD profile (tiered only).
  - `exp5_device_time_per_query_vs_ssd_profile.png` – modeled device time/query vs SSD profile.

## High-level observations

On this 20k-base, 2k-query synthetic workload with 50% cache in tiered mode:
- Recall@10 stays ≈0.998 across DRAM and all SSD profiles.
- Modeled SSD device time per query drops by orders of magnitude as we move from SATA-like to ultra NVMe-like parameters:
  - SATA-like: device_time ≈ 4.5 ms/query.
  - NVMe Gen3: ≈ 0.9 ms/query.
  - NVMe fast: ≈ 0.22 ms/query.
  - NVMe ultra: ≈ 0.03 ms/query.
- Effective QPS for tiered runs improves with faster SSDs but saturates in the low 200s, indicating that host compute and tiered overheads become the limiting factor once device time is small.
- The DRAM baseline (`mode=dram`) achieves much higher effective QPS (≈1.5e3) by design, since it has no modeled device time; it serves as an upper bound when SSD latency is effectively zero.

See `CONCLUSIONS.md` in this directory for a more detailed interpretation of these SSD sensitivity results.
