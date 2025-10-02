# Advanced Computer Systems - Class-wide Projects

Performance engineering projects covering SIMD, cache/memory, and storage profiling.

---

## Projects

- **Project #1**: SIMD Advantage Profiling (vectorization, locality, alignment)
- **Project #2**: Cache & Memory Performance Profiling (latency, bandwidth, intensity)
- **Project #3**: SSD Performance Profiling

---

## Project #1: SIMD Advantage Profiling

### Overview

Quantify SIMD speedup on numeric kernels (SAXPY, dot-product, element-wise multiply, stencil) across working-set sizes, data types, alignments, and strides.

### Build

```bash
# From repository root
cd <root>

# Build all P1 executables (Release mode with CMake)
cmake -S . -B p1/build -DCMAKE_BUILD_TYPE=Release
cmake --build p1/build -j

# Binaries will be in: p1/build/bin/{saxpy,dot,mul,stencil}
```

### Run All Benchmarks

**Recommended**: Run all sweeps and generate plots:

```bash
bash p1/scripts/run_all_p1_sweeps.sh --plot
```

This executes:

- Non-stride sweeps: vary N from 2^12 to 2^26, stride=1
- Stride sweeps: vary stride 1-64, N from 2^12 to 2^26
- All 4 kernels × 3 variants (scalar, auto-vectorized, avx2) × 2 dtypes (f32, f64) × 2 alignments

**Output**: CSVs in `p1/data/raw/`, plots in `p1/plots/`

### Run Individual Kernels

**Non-stride sweeps** (vs array size N):

```bash
bash p1/scripts/run_saxpy_sweep.sh    # → p1/data/raw/p1_saxpy.csv
bash p1/scripts/run_dot_sweep.sh      # → p1/data/raw/p1_dot.csv
bash p1/scripts/run_mul_sweep.sh      # → p1/data/raw/p1_mul.csv
bash p1/scripts/run_stencil_sweep.sh  # → p1/data/raw/p1_stencil.csv
```

**Stride sweeps** (vs stride at multiple N):

```bash
bash p1/scripts/run_saxpy_stride_sweep.sh    # → p1/data/raw/p1_saxpy_stride.csv
bash p1/scripts/run_dot_stride_sweep.sh      # → p1/data/raw/p1_dot_stride.csv
bash p1/scripts/run_mul_stride_sweep.sh      # → p1/data/raw/p1_mul_stride.csv
bash p1/scripts/run_stencil_stride_sweep.sh  # → p1/data/raw/p1_stencil_stride.csv
```

### Generate Plots

After running sweeps, regenerate plots:

```bash
bash p1/scripts/generate_all_plots.sh
```

Custom plotting:

```bash
# Plot SAXPY performance vs N
python3 p1/scripts/plot_p1.py \
  --in p1/data/raw/p1_saxpy.csv \
  --out p1/plots/saxpy_vs_n.png \
  --xaxis n

# Plot SAXPY performance vs stride (at fixed N=1M)
python3 p1/scripts/plot_p1.py \
  --in p1/data/raw/p1_saxpy_stride.csv \
  --out p1/plots/saxpy_vs_stride.png \
  --xaxis stride \
  --fixed_n 1048576
```

### Vectorization Reports

Generate compiler vectorization reports:

```bash
bash p1/scripts/vectorization_reports.sh
# Output: p1/data/raw/p1_vectorize_build.log
```

### Example Manual Runs

Run specific configurations:

```bash
# SAXPY: 1M elements, f32, aligned, stride=1, 5 reps
./p1/build/bin/saxpy --size 1048576 --dtype f32 --reps 5

# DOT: 4M elements, f64, misaligned, stride=2
./p1/build/bin/dot -n 4194304 --dtype f64 --misaligned --stride 2

# MUL: 2^20 elements, f32, stride=4
./p1/build/bin/mul -n $((2**20)) --stride 4

# STENCIL: sweep sizes with f64
for n in 4096 8192 16384 32768; do
  ./p1/build/bin/stencil --size $n --dtype f64 --reps 7
done
```

---

## Project #2: Cache & Memory Performance Profiling

### Overview

Characterize memory hierarchy (latencies, bandwidths, intensity trade-offs) using Intel MLC and custom kernels with perf counters.

### Prerequisites

**Intel MLC**: Download and place in `p2/tools/`

```bash
# Download Intel MLC from: https://www.intel.com/content/www/us/en/developer/articles/tool/intelr-memory-latency-checker.html
# Extract to p2/tools/mlc (Linux) or p2/tools/mlc.exe (Windows)
```

**Python dependencies**:

```bash
pip install numpy pandas matplotlib seaborn
```

### Build P2 Kernels (Linux/WSL)

```bash
cd p2/src
g++ -O3 -march=native -o ../bin/cache_miss_kernel cache_miss_kernel.cpp
g++ -O3 -march=native -o ../bin/tlb_miss_kernel tlb_miss_kernel.cpp
```

**Windows**:

```bash
cd p2/src
cl /O2 /arch:AVX2 /Fe:../bin/cache_miss_kernel.exe cache_miss_kernel.cpp
cl /O2 /arch:AVX2 /Fe:../bin/tlb_miss_kernel.exe tlb_miss_kernel_windows.cpp
```

### Setup & System Info

**First-time setup** (collect system configuration):

**Windows**:

```powershell
cd p2/scripts
.\setup_check.ps1              # Quick environment check
.\collect_system_info.ps1      # Full system info → data/raw/system_info.txt
```

**Linux/WSL**:

```bash
cd p2/scripts
bash setup_env.sh              # Environment setup
bash collect_system_info.sh    # System info → data/raw/system_info.txt
```

### Run Experiments

Experiments are organized in `p2/scripts/exp{1-7}/`. Each has Windows (.ps1) and Linux (.sh) versions.

#### Experiment 1: Zero-Queue Baselines

Measure idle latency for memory hierarchy levels.

**Windows**:

```powershell
cd p2/scripts/exp1
.\exp1_zero_queue.ps1
```

**Linux/WSL**:

```bash
cd p2/scripts/exp1
bash exp1_zero_queue.sh
```

**Output**: `p2/data/raw/exp1_idle_latency.csv`, `exp1_latency_matrix.csv`

#### Experiment 2: Pattern & Granularity

Test sequential/random access with different strides.

**Windows**:

```powershell
cd p2/scripts/exp2
.\exp2_pattern_sweep.ps1
```

**Linux/WSL**:

```bash
cd p2/scripts/exp2
bash exp2_pattern_sweep.sh
```

**Output**: `p2/data/raw/exp2_pattern_results.csv`

#### Experiment 3: Read/Write Mix

Test read/write ratios and bandwidth.

**Linux/WSL** (recommended):

```bash
cd p2/scripts/exp3
bash exp3_rw_mix.sh
```

**Output**: `p2/data/raw/exp3_rw_results.csv`

#### Experiment 4: Intensity Sweep

Measure loaded latency vs. intensity (Little's Law).

```bash
cd p2/scripts/exp4
bash exp4_intensity_sweep.sh
```

**Output**: `p2/data/raw/exp4_intensity_results.csv`

#### Experiment 5: Working-Set Size

```bash
cd p2/scripts/exp5
bash exp5_working_set.sh
```

#### Experiment 6: Cache-Miss Impact

Requires Linux `perf` counters.

```bash
cd p2/scripts/exp6
sudo bash exp6_cache_miss.sh
```

#### Experiment 7: TLB-Miss Impact

Requires Linux `perf` counters.

```bash
cd p2/scripts/exp7
sudo bash exp7_tlb_miss.sh
```

### Analyze Results

After running experiments, analyze with Python scripts:

```bash
cd p2/analysis

# Experiment 1: Latency analysis
python analyze_exp1.py

# Experiment 2: Pattern/stride plots
python analyze_exp2.py

# Experiment 3: Read/write mix analysis
python analyze_exp3.py

# Experiment 4: Intensity sweep & Little's Law
python analyze_exp4.py

# Additional experiments (5-7)
python analyze_exp5.py
python analyze_exp6.py
python analyze_exp7.py
```

**Output**: Tables and plots in `p2/plots/`

### Quick Run All (Windows)

```powershell
# From p2/scripts
.\exp1\exp1_zero_queue.ps1
.\exp2\exp2_pattern_sweep.ps1

cd ..\analysis
python analyze_exp1.py
python analyze_exp2.py
```

### Quick Run All (Linux/WSL)

```bash
# From p2/scripts
bash exp1/exp1_zero_queue.sh
bash exp2/exp2_pattern_sweep.sh
bash exp3/exp3_rw_mix.sh
bash exp4/exp4_intensity_sweep.sh

cd ../analysis
python analyze_exp1.py
python analyze_exp2.py
python analyze_exp3.py
python analyze_exp4.py
```

---

## Data Organization

```
p1/
├── data/raw/          # CSV benchmark results
├── plots/             # Generated plots
└── build/bin/         # Compiled executables

p2/
├── data/raw/          # Experiment results (CSV, JSON)
├── plots/             # Analysis plots and tables
├── bin/               # Custom kernels
└── tools/             # Intel MLC, etc.
```

---

## Requirements

### Software

- **OS**: Linux/WSL (Ubuntu 22.04+) or Windows 10+
- **Compiler**: GCC 9+ or Clang 12+ (MSVC 19+ on Windows)
- **CMake**: 3.16+
- **Python**: 3.8+ with numpy, pandas, matplotlib, seaborn

### Hardware

- x86-64 CPU with AVX2+ (AVX-512 optional)

### Tools

- **Intel MLC**: Memory Latency Checker v3.11+
- **perf**: Linux performance counters (for P2 experiments 6-7)
- **bash/PowerShell**: Scripts available for both platforms

---

## Notes

- **Run from WSL**: P1 and most P2 experiments work best in WSL/Linux (my perf didn't work so I used timing analysis)
- **Administrator/sudo**: Required for MLC experiments
- **Timing variance**: Scripts use multiple repetitions (5-7) and report median
- **Output location**: All data goes to `p{1,2}/data/raw/`, plots to `p{1,2}/plots/`

---

## Troubleshooting

### CMake errors

```bash
# Clean and rebuild
rm -rf p1/build p1/build_vec
cmake -S . -B p1/build -DCMAKE_BUILD_TYPE=Release
cmake --build p1/build -j
```

### MLC not found

```bash
# Verify MLC is in the correct location
ls -l p2/tools/mlc

# Make executable (Linux/WSL)
chmod +x p2/tools/mlc
```

### Permission denied (perf)

```bash
# Experiments 6-7 require sudo
sudo bash p2/scripts/exp6/exp6_cache_miss.sh
```

### Python module errors

```bash
pip install --upgrade numpy pandas matplotlib seaborn
```

---
