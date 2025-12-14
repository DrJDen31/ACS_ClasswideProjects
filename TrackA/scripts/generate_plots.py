#!/usr/bin/env python3
"""
Plotting script for Project A4
Generates all required figures for the report
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import sys
from pathlib import Path

# Set style for publication-quality plots
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['legend.fontsize'] = 10

COLORS = {
    'coarse': '#d62728',  # Red
    'fine': '#2ca02c',    # Green
    'rwlock': '#1f77b4'   # Blue
}

MARKERS = {
    'coarse': 'o',
    'fine': 's',
    'rwlock': '^'
}

LINESTYLES = {
    'lookup': '-',
    'insert': '--',
    'mixed': '-.',
}

# Explicit palette per (strategy, workload) pair to make curves easier to distinguish.
# Coarse: maroon → red-orange → orange-yellow. Fine: green → cyan → blue.
PAIR_COLORS = {
    ('coarse', 'lookup'): '#800000',  # maroon
    ('coarse', 'insert'): '#d55e00',  # burnt orange
    ('coarse', 'mixed'):  '#ffbf00',  # orange-yellow
    ('fine', 'lookup'):   '#2ca02c',  # green
    ('fine', 'insert'):   '#17becf',  # cyan
    ('fine', 'mixed'):    '#1f77b4',  # darker blue
}


def get_variant_color(strategy, workload):
    """Return a distinct color for a (strategy, workload) pair.

    Falls back to the base strategy color if a specific pair is not defined.
    """
    if (strategy, workload) in PAIR_COLORS:
        return PAIR_COLORS[(strategy, workload)]
    base = COLORS.get(strategy, 'gray')
    return mcolors.to_rgb(base)

def load_data(csv_file):
    """Load and preprocess data"""
    df = pd.read_csv(csv_file)
    df = df[df['throughput_ops_sec'] != 'FAILED']
    df['throughput_ops_sec'] = df['throughput_ops_sec'].astype(float)
    df['throughput_mops_sec'] = df['throughput_ops_sec'] / 1e6
    
    # Compute median across repetitions
    stats = df.groupby(['strategy', 'workload', 'threads', 'dataset_size'])['throughput_mops_sec'].median().reset_index()
    stats.columns = ['strategy', 'workload', 'threads', 'dataset_size', 'throughput']
    
    return stats


def plot_strategy_comparison_vs_threads(df, output_dir, dataset_size=100000):
    """Additional plot: coarse vs fine throughput vs threads at a fixed dataset size.

    This directly visualizes the negative scaling of coarse-grained locking versus
    the positive scaling of fine-grained locking at 100K keys (or another chosen
    size present for both strategies).
    """
    print("Generating coarse vs fine strategy comparison plot...")

    workloads = sorted(df['workload'].unique())
    n_workloads = len(workloads)

    fig, axes = plt.subplots(1, n_workloads, figsize=(6 * n_workloads, 5))
    if n_workloads == 1:
        axes = [axes]

    for idx, workload in enumerate(workloads):
        ax = axes[idx]

        wl_data = df[
            (df['workload'] == workload)
            & (df['dataset_size'] == dataset_size)
            & (df['strategy'].isin(['coarse', 'fine']))
        ]

        for strategy in sorted(wl_data['strategy'].unique()):
            strat_data = wl_data[wl_data['strategy'] == strategy].sort_values('threads')
            ax.plot(
                strat_data['threads'],
                strat_data['throughput'],
                marker=MARKERS.get(strategy, 'o'),
                color=COLORS.get(strategy, 'gray'),
                linewidth=2,
                markersize=8,
                label=strategy.capitalize(),
            )

        ax.set_xlabel('Number of Threads')
        ax.set_ylabel('Throughput (Mops/sec)')
        ax.set_title(f"{workload.capitalize()} Workload\\n(Dataset: {dataset_size:,} keys)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_yscale('log')

    plt.tight_layout()
    output_path = Path(output_dir) / f'strategy_comparison_threads_{dataset_size}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_path}")
    plt.close()

def plot_throughput_vs_threads(df, output_dir):
    """Plot 1: Throughput vs Thread Count"""
    print("Generating throughput vs threads plots...")
    
    workloads = df['workload'].unique()
    n_workloads = len(workloads)
    
    fig, axes = plt.subplots(1, n_workloads, figsize=(6*n_workloads, 5))
    if n_workloads == 1:
        axes = [axes]
    
    for idx, workload in enumerate(sorted(workloads)):
        ax = axes[idx]
        wl_data = df[df['workload'] == workload]
        
        # Use largest dataset size for main plot
        size = wl_data['dataset_size'].max()
        size_data = wl_data[wl_data['dataset_size'] == size]
        
        for strategy in sorted(size_data['strategy'].unique()):
            strat_data = size_data[size_data['strategy'] == strategy].sort_values('threads')
            ax.plot(strat_data['threads'], strat_data['throughput'], 
                   marker=MARKERS.get(strategy, 'o'), 
                   color=COLORS.get(strategy, 'gray'),
                   linewidth=2, markersize=8,
                   label=strategy.capitalize())
        
        ax.set_xlabel('Number of Threads')
        ax.set_ylabel('Throughput (Mops/sec)')
        ax.set_title(f'{workload.capitalize()} Workload\n(Dataset: {size:,} keys)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_yscale('log')
        
    plt.tight_layout()
    output_path = Path(output_dir) / 'throughput_vs_threads.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_path}")
    plt.close()

def plot_speedup(df, output_dir):
    """Plot 2: Speedup vs Thread Count"""
    print("Generating speedup plots...")
    
    workloads = df['workload'].unique()
    n_workloads = len(workloads)
    
    fig, axes = plt.subplots(1, n_workloads, figsize=(6*n_workloads, 5))
    if n_workloads == 1:
        axes = [axes]
    
    for idx, workload in enumerate(sorted(workloads)):
        ax = axes[idx]
        wl_data = df[df['workload'] == workload]

        # Use largest dataset size
        size = wl_data['dataset_size'].max()
        size_data = wl_data[wl_data['dataset_size'] == size]

        fine_serial_fraction = None

        for strategy in sorted(size_data['strategy'].unique()):
            strat_data = size_data[size_data['strategy'] == strategy].sort_values('threads')

            # Compute speedup relative to 1 thread
            baseline_data = strat_data[strat_data['threads'] == 1]['throughput'].values
            if len(baseline_data) == 0:
                continue  # Skip if no baseline data
            baseline = baseline_data[0]
            speedup = strat_data['throughput'] / baseline

            # For the fine-grained implementation, estimate an effective serial fraction
            # using Amdahl's Law based on the maximum-thread speedup for this workload.
            if strategy == 'fine':
                max_threads = strat_data['threads'].max()
                max_speedup = speedup.iloc[-1]
                if max_threads > 1 and max_speedup > 1.0:
                    # Amdahl: S(N) = 1 / (s + (1-s)/N). Solve for s using N = max_threads.
                    inv_sN = 1.0 / max_speedup
                    numerator = inv_sN - 1.0 / max_threads
                    denominator = 1.0 - 1.0 / max_threads
                    if denominator > 0:
                        fine_serial_fraction = max(0.0, min(1.0, numerator / denominator))

            ax.plot(
                strat_data['threads'],
                speedup,
                marker=MARKERS.get(strategy, 'o'),
                color=COLORS.get(strategy, 'gray'),
                linewidth=2,
                markersize=8,
                label=strategy.capitalize(),
            )

        # Plot Amdahl-law fit for the fine-grained implementation, if available
        threads = sorted(size_data['threads'].unique())
        if fine_serial_fraction is not None:
            amdahl_speedup = [
                1.0 / (fine_serial_fraction + (1.0 - fine_serial_fraction) / t)
                for t in threads
            ]
            ax.plot(
                threads,
                amdahl_speedup,
                'k-.',
                alpha=0.7,
                linewidth=1.5,
                label='Amdahl fit (fine)',
            )

        # Plot ideal linear speedup
        ax.plot(threads, threads, 'k--', alpha=0.5, linewidth=1.5, label='Ideal Linear')
        
        ax.set_xlabel('Number of Threads')
        ax.set_ylabel('Speedup (vs 1 thread)')
        ax.set_title(f'{workload.capitalize()} Workload\n(Dataset: {size:,} keys)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
    plt.tight_layout()
    output_path = Path(output_dir) / 'speedup.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_path}")
    plt.close()

def plot_workload_comparison(df, output_dir):
    """Plot 3: Workload Comparison (bar chart)"""
    print("Generating workload comparison plot...")
    
    # Fixed thread count for comparison (e.g., 8)
    thread_count = 8
    # Use largest dataset size
    size = df['dataset_size'].max()
    
    data = df[(df['threads'] == thread_count) & (df['dataset_size'] == size)]
    
    strategies = sorted(data['strategy'].unique())
    workloads = sorted(data['workload'].unique())
    
    x = np.arange(len(workloads))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for i, strategy in enumerate(strategies):
        strat_data = data[data['strategy'] == strategy]
        throughputs = [strat_data[strat_data['workload'] == wl]['throughput'].values[0] 
                      for wl in workloads]
        
        offset = width * (i - len(strategies)/2 + 0.5)
        ax.bar(x + offset, throughputs, width, 
               label=strategy.capitalize(),
               color=COLORS.get(strategy, 'gray'))
    
    ax.set_xlabel('Workload Type')
    ax.set_ylabel('Throughput (Mops/sec)')
    ax.set_title(f'Workload Comparison\n({thread_count} threads, {size:,} keys)')
    ax.set_xticks(x)
    ax.set_xticklabels([w.capitalize() for w in workloads])
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    output_path = Path(output_dir) / 'workload_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_path}")
    plt.close()

def plot_dataset_size_sensitivity(df, output_dir):
    """Plot 4: Dataset Size Sensitivity"""
    print("Generating dataset size sensitivity plot...")
    
    # Fixed thread count (e.g., 8)
    thread_count = 8
    
    workloads = df['workload'].unique()
    n_workloads = len(workloads)
    
    fig, axes = plt.subplots(1, n_workloads, figsize=(6*n_workloads, 5))
    if n_workloads == 1:
        axes = [axes]
    
    for idx, workload in enumerate(sorted(workloads)):
        ax = axes[idx]
        wl_data = df[(df['workload'] == workload) & (df['threads'] == thread_count)]
        
        for strategy in sorted(wl_data['strategy'].unique()):
            strat_data = wl_data[wl_data['strategy'] == strategy].sort_values('dataset_size')
            
            ax.plot(strat_data['dataset_size'], strat_data['throughput'],
                   marker=MARKERS.get(strategy, 'o'),
                   color=COLORS.get(strategy, 'gray'),
                   linewidth=2, markersize=8,
                   label=strategy.capitalize())
        
        ax.set_xlabel('Dataset Size (number of keys)')
        ax.set_ylabel('Throughput (Mops/sec)')
        ax.set_title(f'{workload.capitalize()} Workload\n({thread_count} threads)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xscale('log')
        
    plt.tight_layout()
    output_path = Path(output_dir) / 'dataset_size_sensitivity.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_path}")
    plt.close()


def plot_workload_strategy_dataset_sweep(df, output_dir):
    """Additional plot: throughput vs dataset size for all workloads and strategies on one set of axes.

    This supplements the simple workload-comparison bar chart by sweeping the dataset size (10K--1M keys)
    on the x-axis at a fixed thread count and drawing one line per (strategy, workload) pair, yielding
    six lines total (coarse/fine × lookup/insert/mixed).
    """
    print("Generating workload+strategy dataset sweep plot...")

    # Match other dataset-size plots: fix thread count to 8
    thread_count = 8
    data = df[df['threads'] == thread_count]

    workloads = sorted(data['workload'].unique())
    strategies = sorted(data['strategy'].unique())

    fig, ax = plt.subplots(figsize=(10, 6))

    for strategy in strategies:
        for workload in workloads:
            subset = data[
                (data['strategy'] == strategy)
                & (data['workload'] == workload)
            ].sort_values('dataset_size')

            if subset.empty:
                continue

            label = f"{strategy.capitalize()} {workload.capitalize()}"
            ax.plot(
                subset['dataset_size'],
                subset['throughput'],
                marker=MARKERS.get(strategy, 'o'),
                color=get_variant_color(strategy, workload),
                linestyle='-',  # all solid; workload is encoded via shade rather than style
                linewidth=2,
                markersize=7,
                label=label,
            )

    ax.set_xlabel('Dataset Size (number of keys)')
    ax.set_ylabel('Throughput (Mops/sec)')
    ax.set_title(f'Throughput vs. Dataset Size by Strategy and Workload\n({thread_count} threads)')
    ax.set_xscale('log')
    # Use a log scale on the y-axis as well to separate low-throughput coarse lines
    # from high-throughput fine lines without flattening the smaller values.
    ax.set_yscale('log')
    ax.set_ylim(bottom=1e-2)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = Path(output_dir) / 'workload_strategy_dataset_sweep.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_path}")
    plt.close()


def plot_workload_strategy_dataset_sweep_split(df, output_dir):
    """Variant of the dataset sweep: 1x2 subplot with separate axes for coarse and fine.

    Uses log scale on the x-axis (dataset size) and linear scale on the y-axis so that each
    strategy panel can pick its own natural range without coarse lines being compressed by
    much higher fine-grained throughput.
    """
    print("Generating workload+strategy dataset sweep (split panels) plot...")

    thread_count = 8
    data = df[df['threads'] == thread_count]

    workloads = sorted(data['workload'].unique())
    strategies = ['coarse', 'fine']

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=False)

    for idx, strategy in enumerate(strategies):
        ax = axes[idx]
        strat_data = data[data['strategy'] == strategy]

        for workload in workloads:
            subset = strat_data[strat_data['workload'] == workload].sort_values('dataset_size')
            if subset.empty:
                continue

            label = f"{workload.capitalize()}"
            ax.plot(
                subset['dataset_size'],
                subset['throughput'],
                marker=MARKERS.get(strategy, 'o'),
                color=get_variant_color(strategy, workload),
                linestyle='-',
                linewidth=2,
                markersize=7,
                label=label,
            )

        ax.set_xlabel('Dataset Size (keys)')
        ax.set_xscale('log')
        ax.grid(True, alpha=0.3)
        ax.set_title(f"{strategy.capitalize()} ({thread_count} threads)")
        ax.legend()

    axes[0].set_ylabel('Throughput (Mops/sec)')

    plt.tight_layout()
    output_path = Path(output_dir) / 'workload_strategy_dataset_sweep_split.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_path}")
    plt.close()

def plot_scaling_efficiency(df, output_dir):
    """Plot 5: Parallel Efficiency"""
    print("Generating parallel efficiency plot...")
    
    workloads = df['workload'].unique()
    n_workloads = len(workloads)
    
    fig, axes = plt.subplots(1, n_workloads, figsize=(6*n_workloads, 5))
    if n_workloads == 1:
        axes = [axes]
    
    for idx, workload in enumerate(sorted(workloads)):
        ax = axes[idx]
        wl_data = df[df['workload'] == workload]
        
        # Use largest dataset size
        size = wl_data['dataset_size'].max()
        size_data = wl_data[wl_data['dataset_size'] == size]
        
        for strategy in sorted(size_data['strategy'].unique()):
            strat_data = size_data[size_data['strategy'] == strategy].sort_values('threads')
            
            # Compute efficiency: (speedup / threads) * 100
            baseline_data = strat_data[strat_data['threads'] == 1]['throughput'].values
            if len(baseline_data) == 0:
                continue  # Skip if no baseline data
            baseline = baseline_data[0]
            speedup = strat_data['throughput'] / baseline
            efficiency = (speedup / strat_data['threads']) * 100
            
            ax.plot(strat_data['threads'], efficiency,
                   marker=MARKERS.get(strategy, 'o'),
                   color=COLORS.get(strategy, 'gray'),
                   linewidth=2, markersize=8,
                   label=strategy.capitalize())
        
        # 100% efficiency line
        threads = sorted(df['threads'].unique())
        ax.axhline(y=100, color='k', linestyle='--', alpha=0.5, linewidth=1.5, label='Ideal (100%)')
        
        ax.set_xlabel('Number of Threads')
        ax.set_ylabel('Parallel Efficiency (%)')
        ax.set_title(f'{workload.capitalize()} Workload\n(Dataset: {size:,} keys)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 110)
        
    plt.tight_layout()
    output_path = Path(output_dir) / 'parallel_efficiency.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_path}")
    plt.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_plots.py <results.csv> [output_dir]")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    # Default output directory standardized to results/analysis/plots
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '../results/analysis/plots'
    
    print(f"Loading data from: {csv_file}")
    df = load_data(csv_file)
    
    print(f"Loaded {len(df)} configurations")
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print("\nGenerating plots...")
    plot_throughput_vs_threads(df, output_dir)
    plot_speedup(df, output_dir)
    plot_workload_comparison(df, output_dir)
    plot_dataset_size_sensitivity(df, output_dir)
    plot_workload_strategy_dataset_sweep(df, output_dir)
    plot_workload_strategy_dataset_sweep_split(df, output_dir)
    plot_scaling_efficiency(df, output_dir)
    # New figures: direct coarse vs fine comparisons vs threads at 100K and 500K keys.
    plot_strategy_comparison_vs_threads(df, output_dir, dataset_size=100000)
    plot_strategy_comparison_vs_threads(df, output_dir, dataset_size=500000)
    
    print("\n" + "="*60)
    print("All plots generated successfully!")
    print(f"Plots saved to: {output_dir}/")
    print("="*60)

if __name__ == '__main__':
    main()
