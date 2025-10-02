#!/usr/bin/env python3
"""
Experiment 1 Analysis: Zero-Queue Baselines
Generates latency table and basic plots
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path

# Configuration
DATA_FILE = Path("../data/raw/exp1_zero_queue.csv")
OUTPUT_DIR = Path("../plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    """Load experiment data"""
    if not DATA_FILE.exists():
        print(f"Error: Data file not found: {DATA_FILE}")
        sys.exit(1)
    
    df = pd.read_csv(DATA_FILE)
    print(f"Loaded {len(df)} measurements")
    return df

def compute_statistics(df):
    """Compute statistics for each metric"""
    stats = []
    
    for metric in df['metric'].unique():
        data = df[df['metric'] == metric]['value_ns']
        
        stats.append({
            'Metric': metric,
            'Mean (ns)': data.mean(),
            'Median (ns)': data.median(),
            'Std Dev (ns)': data.std(),
            'Min (ns)': data.min(),
            'Max (ns)': data.max(),
            'CV (%)': (data.std() / data.mean()) * 100,
            'N': len(data)
        })
    
    return pd.DataFrame(stats)

def create_latency_table(stats_df, cpu_freq_mhz=3301):
    """Create formatted latency table with cycle conversion"""
    print("\n" + "="*80)
    print("EXPERIMENT 1: ZERO-QUEUE LATENCY BASELINES")
    print("="*80)
    print(f"\nCPU Frequency: {cpu_freq_mhz} MHz\n")
    
    # Calculate cycles
    ns_per_cycle = 1000 / cpu_freq_mhz
    
    print(f"{'Metric':<30} {'Mean (ns)':<12} {'Cycles':<10} {'Std Dev':<12} {'CV (%)':<8}")
    print("-" * 80)
    
    for _, row in stats_df.iterrows():
        mean_ns = row['Mean (ns)']
        cycles = mean_ns / ns_per_cycle
        std_ns = row['Std Dev (ns)']
        cv = row['CV (%)']
        
        metric_name = row['Metric'].replace('_', ' ').title()
        print(f"{metric_name:<30} {mean_ns:>10.2f}   {cycles:>8.1f}   {std_ns:>10.2f}   {cv:>6.2f}")
    
    print("-" * 80)
    print(f"\nNote: Cycles calculated assuming {cpu_freq_mhz} MHz CPU frequency")
    print(f"      1 cycle = {ns_per_cycle:.3f} ns")
    
    # Save to file
    table_file = OUTPUT_DIR / "exp1_latency_table.txt"
    with open(table_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write("EXPERIMENT 1: ZERO-QUEUE LATENCY BASELINES\n")
        f.write("="*80 + "\n\n")
        f.write(f"CPU Frequency: {cpu_freq_mhz} MHz\n\n")
        f.write(f"{'Metric':<30} {'Mean (ns)':<12} {'Cycles':<10} {'Std Dev':<12} {'CV (%)':<8}\n")
        f.write("-" * 80 + "\n")
        
        for _, row in stats_df.iterrows():
            mean_ns = row['Mean (ns)']
            cycles = mean_ns / ns_per_cycle
            std_ns = row['Std Dev (ns)']
            cv = row['CV (%)']
            
            metric_name = row['Metric'].replace('_', ' ').title()
            f.write(f"{metric_name:<30} {mean_ns:>10.2f}   {cycles:>8.1f}   {std_ns:>10.2f}   {cv:>6.2f}\n")
        
        f.write("-" * 80 + "\n")
        f.write(f"\nNote: Cycles calculated assuming {cpu_freq_mhz} MHz CPU frequency\n")
        f.write(f"      1 cycle = {ns_per_cycle:.3f} ns\n")
    
    print(f"\nTable saved to: {table_file}")

def plot_latencies(df, stats_df):
    """Create bar plot of latencies with error bars"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    metrics = stats_df['Metric'].tolist()
    means = stats_df['Mean (ns)'].tolist()
    stds = stats_df['Std Dev (ns)'].tolist()
    
    x = np.arange(len(metrics))
    bars = ax.bar(x, means, yerr=stds, capsize=5, alpha=0.7, color='steelblue', edgecolor='black')
    
    ax.set_xlabel('Memory Level', fontsize=12, fontweight='bold')
    ax.set_ylabel('Latency (ns)', fontsize=12, fontweight='bold')
    ax.set_title('Experiment 1: Zero-Queue Latencies', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([m.replace('_', '\n') for m in metrics], rotation=0, ha='center')
    
    # Zoom in on the actual data range to make differences visible
    min_val = min(means) - max(stds) - 2
    max_val = max(means) + max(stds) + 2
    ax.set_ylim([min_val, max_val])
    
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Add value labels on bars
    for i, (bar, mean, std) in enumerate(zip(bars, means, stds)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + std,
                f'{mean:.1f}±{std:.1f}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    plot_file = OUTPUT_DIR / "exp1_latencies.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {plot_file}")
    plt.close()

def plot_distribution(df):
    """Create distribution plots for each metric"""
    metrics = df['metric'].unique()
    n_metrics = len(metrics)
    
    fig, axes = plt.subplots(1, n_metrics, figsize=(5*n_metrics, 4))
    if n_metrics == 1:
        axes = [axes]
    
    for ax, metric in zip(axes, metrics):
        data = df[df['metric'] == metric]['value_ns']
        
        ax.hist(data, bins=10, alpha=0.7, color='steelblue', edgecolor='black')
        ax.axvline(data.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {data.mean():.2f}')
        ax.axvline(data.median(), color='green', linestyle='--', linewidth=2, label=f'Median: {data.median():.2f}')
        
        ax.set_xlabel('Latency (ns)', fontsize=10)
        ax.set_ylabel('Frequency', fontsize=10)
        ax.set_title(metric.replace('_', ' ').title(), fontsize=11, fontweight='bold')
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3, linestyle='--')
    
    plt.suptitle('Experiment 1: Latency Distributions', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plot_file = OUTPUT_DIR / "exp1_distributions.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Distribution plot saved to: {plot_file}")
    plt.close()

def main():
    print("Analyzing Experiment 1: Zero-Queue Baselines")
    print("=" * 80)
    
    # Load data
    df = load_data()
    
    # Compute statistics
    stats_df = compute_statistics(df)
    
    # Create latency table
    create_latency_table(stats_df)
    
    # Create plots
    print("\nGenerating plots...")
    plot_latencies(df, stats_df)
    plot_distribution(df)
    
    # Check data quality
    print("\n" + "="*80)
    print("DATA QUALITY CHECK")
    print("="*80)
    
    quality_ok = True
    for _, row in stats_df.iterrows():
        cv = row['CV (%)']
        metric = row['Metric']
        
        if cv > 5.0:
            print(f"⚠ WARNING: {metric} has high variation (CV={cv:.2f}%)")
            print(f"           Consider re-running with more reps or better isolation")
            quality_ok = False
        else:
            print(f"✓ {metric}: CV={cv:.2f}% (Good)")
    
    if quality_ok:
        print("\n✓ All measurements have acceptable variation (<5%)")
    else:
        print("\n⚠ Some measurements have high variation - review experimental setup")
    
    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)

if __name__ == "__main__":
    main()
