# Experiment 12: Unified Cross-Solution Comparison

Compare all solutions under a single, consistent harness:

- hnswlib (external DRAM reference)
- our DRAM HNSW (`benchmark_recall --mode dram`)
- our tiered HNSW (`benchmark_recall --mode tiered`)
- ANN-in-SSD simulator (`benchmark_recall --mode ann_ssd`, levels L0–L3)

## How to run

From the project root under WSL:

```bash
cd experiments/Experiment12_Unified_Comparison
./scripts/experiment12.sh --quick
python3 scripts/analyze_experiment12.py
```

Use `--quick` to run a smaller subset (SIFT20k + synthetic20k). Omit it to include the extra SIFT100k point.

## Outputs

- Raw JSON logs: `results/raw/exp12_*.json`
- Plots:
  - `results/plots/exp12_SIFT1M_recall_vs_effective_qps.png`
  - `results/plots/exp12_synthetic_gaussian_recall_vs_effective_qps.png`

## Notes

- For SIFT subset runs, we use the provided `sift_groundtruth.ivecs` and filter out-of-range neighbor IDs when `num_base < 1M`. This can depress the absolute recall values at smaller subset sizes; the effect is consistent across all solutions in the unified run.
- You need `hnswlib` installed in the WSL Python environment: `pip install hnswlib`.
