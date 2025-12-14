#!/usr/bin/env python3
"""
Experiment 3 Analysis: Read/Write Mix Sweep
Generates bandwidth comparison plots for different R/W ratios
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path

# Configuration
DATA_FILE = Path("../data/raw/exp3_rw_mix.csv")
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
    """Compute statistics for each R/W ratio"""
    stats = []
    
    for ratio in df['ratio'].unique():
        data = df[df['ratio'] == ratio]['bandwidth_mbps']
        
        stats.append({
            'Ratio': ratio,
            'Read %': df[df['ratio'] == ratio]['read_pct'].iloc[0],
            'Write %': df[df['ratio'] == ratio]['write_pct'].iloc[0],
            'BW Mean (MB/s)': data.mean(),
            'BW Std (MB/s)': data.std(),
            'BW Min (MB/s)': data.min(),
            'BW Max (MB/s)': data.max(),
            'CV (%)': (data.std() / data.mean()) * 100,
            'N': len(data)
        })
    
    return pd.DataFrame(stats)

def plot_bandwidth_comparison(stats_df):
    """Create bar plot comparing bandwidth across R/W ratios"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Sort by read percentage
    stats_df = stats_df.sort_values('Read %', ascending=False)
    
    x = np.arange(len(stats_df))
    means = stats_df['BW Mean (MB/s)'].values
    stds = stats_df['BW Std (MB/s)'].values
    labels = stats_df['Ratio'].values
    
    # Color code by ratio
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
    
    bars = ax.bar(x, means, yerr=stds, capsize=5, alpha=0.8, 
                  color=colors[:len(x)], edgecolor='black', linewidth=1.5)
    
    ax.set_xlabel('Read/Write Ratio', fontsize=12, fontweight='bold')
    ax.set_ylabel('Bandwidth (MB/s)', fontsize=12, fontweight='bold')
    ax.set_title('Experiment 3: Bandwidth vs Read/Write Mix', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0, ha='center')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Add value labels on bars
    for bar, mean, std in zip(bars, means, stds):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + std,
                f'{mean:.0f}±{std:.0f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plot_file = OUTPUT_DIR / "exp3_rw_bandwidth.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {plot_file}")
    plt.close()

def plot_normalized_performance(stats_df):
    """Create plot showing performance normalized to 100% read"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    stats_df = stats_df.sort_values('Read %', ascending=False)
    
    # Normalize to all reads baseline
    baseline = stats_df[stats_df['Ratio'] == 'All Reads']['BW Mean (MB/s)'].values[0]
    normalized = (stats_df['BW Mean (MB/s)'] / baseline) * 100
    
    x = np.arange(len(stats_df))
    bars = ax.bar(x, normalized, alpha=0.8, color='steelblue', edgecolor='black', linewidth=1.5)
    
    # Add baseline line
    ax.axhline(y=100, color='red', linestyle='--', linewidth=2, label='All Reads Baseline')
    
    ax.set_xlabel('Read/Write Ratio', fontsize=12, fontweight='bold')
    ax.set_ylabel('Normalized Bandwidth (%)', fontsize=12, fontweight='bold')
    ax.set_title('Experiment 3: Normalized Performance (vs All Reads)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(stats_df['Ratio'].values, rotation=0, ha='center')
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Add value labels
    for bar, val in zip(bars, normalized):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}%',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plot_file = OUTPUT_DIR / "exp3_normalized.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Normalized plot saved to: {plot_file}")
    plt.close()

def create_summary_table(stats_df):
    """Create formatted summary table"""
    print("\n" + "="*80)
    print("EXPERIMENT 3: READ/WRITE MIX SWEEP RESULTS")
    print("="*80)
    print(f"\n{'Ratio':<15} {'Read%':<8} {'Write%':<8} {'Bandwidth (MB/s)':<20} {'CV (%)':<8}")
    print("-" * 80)
    
    # Sort by read percentage
    stats_df = stats_df.sort_values('Read %', ascending=False)
    
    for _, row in stats_df.iterrows():
        ratio = row['Ratio']
        read_pct = f"{row['Read %']:.0f}%"
        write_pct = f"{row['Write %']:.0f}%"
        bw = f"{row['BW Mean (MB/s)']:.1f} ± {row['BW Std (MB/s)']:.1f}"
        cv = f"{row['CV (%)']:.2f}"
        
        print(f"{ratio:<15} {read_pct:<8} {write_pct:<8} {bw:<20} {cv:<8}")
    
    print("-" * 80)
    
    # Calculate performance degradation
    baseline = stats_df[stats_df['Ratio'] == 'All Reads']['BW Mean (MB/s)'].values[0]
    print(f"\nBaseline (All Reads): {baseline:.1f} MB/s")
    print("\nPerformance vs All Reads:")
    for _, row in stats_df.iterrows():
        ratio = row['Ratio']
        pct = (row['BW Mean (MB/s)'] / baseline) * 100
        degradation = 100 - pct
        print(f"  {ratio:<20}: {pct:>5.1f}% ({degradation:+.1f}% change)")
    
    # Save to file
    table_file = OUTPUT_DIR / "exp3_summary_table.txt"
    with open(table_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write("EXPERIMENT 3: READ/WRITE MIX SWEEP RESULTS\n")
        f.write("="*80 + "\n\n")
        f.write(f"{'Ratio':<15} {'Read%':<8} {'Write%':<8} {'Bandwidth (MB/s)':<20} {'CV (%)':<8}\n")
        f.write("-" * 80 + "\n")
        
        for _, row in stats_df.iterrows():
            ratio = row['Ratio']
            read_pct = f"{row['Read %']:.0f}%"
            write_pct = f"{row['Write %']:.0f}%"
            bw = f"{row['BW Mean (MB/s)']:.1f} ± {row['BW Std (MB/s)']:.1f}"
            cv = f"{row['CV (%)']:.2f}"
            
            f.write(f"{ratio:<15} {read_pct:<8} {write_pct:<8} {bw:<20} {cv:<8}\n")
        
        f.write("-" * 80 + "\n")
        f.write(f"\nBaseline (100% Read): {baseline:.1f} MB/s\n")
        f.write("\nPerformance vs 100% Read:\n")
        for _, row in stats_df.iterrows():
            ratio = row['Ratio']
            pct = (row['BW Mean (MB/s)'] / baseline) * 100
            degradation = 100 - pct
            f.write(f"  {ratio:<15}: {pct:>5.1f}% ({degradation:+.1f}% change)\n")
    
    print(f"\nTable saved to: {table_file}")

def main():
    print("Analyzing Experiment 3: Read/Write Mix Sweep")
    print("=" * 80)
    
    # Load data
    df = load_data()
    
    # Compute statistics
    stats_df = compute_statistics(df)
    
    # Create summary table
    create_summary_table(stats_df)
    
    # Create plots
    print("\nGenerating plots...")
    plot_bandwidth_comparison(stats_df)
    plot_normalized_performance(stats_df)
    
    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)
    print("\nKey Insights:")
    print("- Compare read vs write bandwidth")
    print("- Observe impact of mixed R/W on performance")
    print("- Consider hardware effects (write buffers, combining)")

if __name__ == "__main__":
    main()
