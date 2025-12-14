# Experiment 9: ANN-in-SSD vs Tiered vs DRAM

Compare the three main solutions on a common dataset and workload:

- DRAM-only HNSW (`mode=dram`).
- Tiered DRAM+SSD HNSW (`mode=tiered`).
- ANN-in-SSD simulator (`mode=ann_ssd`).

Measure recall@k, QPS, latency percentiles, IO stats, and modeled `device_time_us`.

## How to run

From the project root under WSL:

```bash
cd experiments/Experiment9_AnnSSD_vs_Tiered_vs_DRAM
./scripts/experiment9.sh
python3 scripts/analyze_experiment9.py
```

The driver reads parameters from `config/experiment9.conf`.

## Outputs

- Raw JSON logs: `results/raw/exp9_*.json`
- Plot(s): `results/plots/`
  - `exp9_synthetic_gaussian_recall_qps.png`

## Notes

- This experiment can be switched from synthetic to real SIFT by setting `DATASET_PATH`, `QUERY_PATH`, and `GROUNDTRUTH_PATH` in `config/experiment9.conf`.
- The Experiment 9 driver has been patched to ensure **ANN-in-SSD uses the same dataset/queries/ground-truth** as DRAM/tiered when those paths are provided.
