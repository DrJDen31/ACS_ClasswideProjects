# B2: Tier-Aware + ANN-in-SSD Approximate Nearest-Neighbor Search

Exploiting high-IOPS SSDs for billion-scale vector search with quantified recall-latency-cost trade-offs, plus an experimental graph-in-flash ANN-in-SSD model that assumes no system DRAM.

[Report](https://github.com/DrJDen31/ACS_ClasswideProjects/blob/master/FinalProjects/TrackB/report/ACS_Final_Track_B_Project.pdf)

## Quick Start

For step-by-step instructions on building the project, running all experiments, generating plots, and refreshing the report figures, see:

`QUICKSTART.md`

That document covers both the "run everything" scripts and per-experiment options.

## Project Structure

- `src/` – Core implementation (vector operations, HNSW, storage backends, tiering logic, ANN-in-SSD simulator)
- `experiments/` – Per-experiment drivers and analysis scripts for Experiments 0–12
- `scripts/` – Helper scripts, including `run_all_experiments*.sh`, `run_all_plots.sh`, and `refresh_all_plots.ps1`
- `data/` – Datasets (e.g., SIFT1M) used by selected experiments
- `tests/` – Unit and integration tests
- `benchmarks/` – Legacy benchmark harness and dataset utilities
- `docs/` – Design documentation
- `report/` – LaTeX report (`B2-Report.tex`) and final figures in `report/plots/`

## Key Metrics

- **Recall@k** – Search quality (% of true k-NN retrieved)
- **QPS / Effective QPS** – Throughput (queries per second), including analytic effective QPS
- **I/O Amplification** – Bytes read per query relative to vector size
- **Latency** – p50, p95, p99 query latency
- **Cost** – $/GB DRAM vs SSD and derived cost-per-QPS metrics

## Implementation Plan

See `B2-Implementation-Plan.md` for the detailed roadmap and design decisions.

## Reproducing Results (High-Level)

1. Build the project (inside WSL/Linux): `make all`
2. Run all experiments and plots (inside WSL/Linux): `./scripts/run_all_experiments_and_plots.sh`
3. Refresh the figures used in the LaTeX report (Windows PowerShell): `./scripts/refresh_all_plots.ps1`

For finer-grained control (individual experiments, quick runs, etc.), refer to `QUICKSTART.md`.

## References

- DiskANN: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node (NIPS 2019)
- SPANN: Highly-efficient Billion-scale Approximate Nearest Neighbor Search (NIPS 2021)
- Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs (TPAMI 2018)
