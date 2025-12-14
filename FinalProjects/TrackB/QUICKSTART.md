# B2 Quick Start

This quick start guide explains how to build the B2 project, run the experiments, generate plots, and refresh the figures used in the report.

Most of the automated scripts assume:

- You build and run experiments inside **Linux or WSL** (for the C++ benchmark and Python analysis scripts).
- You refresh figures for the LaTeX report from **Windows PowerShell** using a helper script.

---

## 1. Build the project

From the `TrackB` project root (inside WSL or another Linux environment):

```bash
cd /path/to/TrackB
make all
```

This builds the `bin/benchmark_recall` binary and any other required tools.

If you have not yet downloaded datasets (e.g., SIFT1M), follow the dataset instructions in `B2-Implementation-Plan.md` or the scripts under `benchmarks/`.

---

## 2. Option A – Run _all_ experiments and plots

This is the easiest way to regenerate every experiment (0–12) and their plots.

### Step 1 – Run all experiments (WSL/Linux)

From the `TrackB` project root in WSL:

```bash
./scripts/run_all_experiments_and_plots.sh
```

This script:

- Runs `experiment0.sh` through `experiment12.sh` under `experiments/Experiment*/scripts/`.
- Invokes all `analyze_experiment*.py` scripts to regenerate plots in `experiments/Experiment*/results/plots/`.

You can also run the two phases separately if desired:

```bash
# Only run experiments (no plots)
./scripts/run_all_experiments.sh

# Only run analysis/plot scripts (on existing JSON results)
./scripts/run_all_plots.sh
```

### Step 2 – Copy plots into the report (Windows PowerShell)

From Windows PowerShell at the same `TrackB` project root:

```powershell
cd "path\to\TrackB"

# Dry run: show which plots would be copied
./scripts/refresh_all_plots.ps1 -WhatIf

# Actual copy: refresh all plots referenced in B2-Report.tex
./scripts/refresh_all_plots.ps1
```

The PowerShell script copies only the PNGs that are actually referenced in `report/B2-Report.tex` from the various `experiments/*/results/plots` directories into `report/plots/`.

---

## 3. Option B – Run a single experiment and its plots

Sometimes you only want to rerun or tweak one experiment.

### Step 1 – Run the experiment (WSL/Linux)

Each experiment has its own driver script under `experiments/Experiment*/scripts/`. For example:

```bash
# Experiment 8 – SOTA comparison
cd /path/to/TrackB
cd experiments/Experiment8_Compare_SOTA
./scripts/experiment8.sh

# Experiment 10 – ANN-in-SSD design space
cd /path/to/TrackB
cd experiments/Experiment10_AnnSSD_Design_Space
./scripts/experiment10.sh
```

These scripts write JSON logs under the corresponding `results/raw/` directories.

### Step 2 – Generate plots for that experiment

From the `TrackB` project root in WSL, call the appropriate analysis script. For example:

```bash
# Experiment 8 plots
python experiments/Experiment8_Compare_SOTA/scripts/analyze_experiment8.py

# Experiment 10 plots
python experiments/Experiment10_AnnSSD_Design_Space/scripts/analyze_experiment10.py

# Experiment 12 unified comparison
python experiments/Experiment12_Unified_Comparison/scripts/analyze_experiment12.py
```

Each analysis script reads JSON files from that experiment's `results/raw/` directory and writes PNGs into `results/plots/` under the same experiment.

### Step 3 – Refresh report figures

After regenerating plots for one or more experiments, refresh the figures used in the LaTeX report:

```powershell
cd "path\to\TrackB"
./scripts/refresh_all_plots.ps1
```

This copies the updated subset of PNGs into `report/plots/` so that a subsequent LaTeX build of `report/B2-Report.tex` includes the latest versions.

---

## 4. Troubleshooting

- **Missing `hnswlib`** – Some experiments (e.g., Experiment 8, Experiment 12) require the Python `hnswlib` package for baseline runs. Install it in your WSL Python environment, for example:

  ```bash
  pip install hnswlib matplotlib
  ```

  (Adjust the command to match your environment or virtualenv setup.)

- **Matplotlib not available** – If the analysis scripts print `[INFO] matplotlib not available; skipping plots.`, install `matplotlib` in the Python environment where you run the analysis scripts.
- **Long runtimes** – Running all experiments (especially Experiment 12 with larger datasets) can take significant time. Use the per-experiment scripts if you only need to refresh a subset of figures.
