#!/usr/bin/env python3
"""
Experiment 2 Analysis: Pattern & Granularity Sweep
Generates bandwidth and latency plots for different access patterns and strides
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path

# Configuration
DATA_FILE = Path("../data/raw/exp2_pattern_sweep.csv")
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
    """Compute statistics grouped by pattern and stride"""
    stats = []
    
    for pattern in df['pattern'].unique():
        pattern_df = df[df['pattern'] == pattern]
        
        for stride in sorted(pattern_df['stride_bytes'].unique()):
            stride_df = pattern_df[pattern_df['stride_bytes'] == stride]
            
            bw_data = stride_df['bandwidth_mbps'].dropna()
            lat_data = stride_df['loaded_latency_ns'].dropna()
            
            stats.append({
                'Pattern': pattern,
                'Stride (B)': stride,
                'BW Mean (MB/s)': bw_data.mean() if len(bw_data) > 0 else np.nan,
                'BW Std (MB/s)': bw_data.std() if len(bw_data) > 0 else np.nan,
                'Latency Mean (ns)': lat_data.mean() if len(lat_data) > 0 else np.nan,
                'Latency Std (ns)': lat_data.std() if len(lat_data) > 0 else np.nan,
                'N': len(stride_df)
            })
    
    return pd.DataFrame(stats)

def plot_bandwidth_comparison(stats_df):
    """Create grouped bar plot for bandwidth across patterns and strides"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    patterns = stats_df['Pattern'].unique()
    strides = sorted(stats_df['Stride (B)'].unique())
    
    x = np.arange(len(strides))
    width = 0.35
    
    for i, pattern in enumerate(patterns):
        pattern_data = stats_df[stats_df['Pattern'] == pattern]
        means = [pattern_data[pattern_data['Stride (B)'] == s]['BW Mean (MB/s)'].values[0] 
                 if len(pattern_data[pattern_data['Stride (B)'] == s]) > 0 else 0 
                 for s in strides]
        stds = [pattern_data[pattern_data['Stride (B)'] == s]['BW Std (MB/s)'].values[0] 
                if len(pattern_data[pattern_data['Stride (B)'] == s]) > 0 else 0 
                for s in strides]
        
        offset = width * (i - len(patterns)/2 + 0.5)
        bars = ax.bar(x + offset, means, width, yerr=stds, 
                     label=pattern.capitalize(), capsize=5, alpha=0.8)
        
        # Add value labels
        for bar, mean, std in zip(bars, means, stds):
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + std,
                       f'{mean:.0f}',
                       ha='center', va='bottom', fontsize=8)
    
    ax.set_xlabel('Stride (Bytes)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Bandwidth (MB/s)', fontsize=12, fontweight='bold')
    ax.set_title('Experiment 2: Bandwidth vs Stride and Pattern', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{s}B' for s in strides])
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plot_file = OUTPUT_DIR / "exp2_bandwidth_comparison.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Bandwidth plot saved to: {plot_file}")
    plt.close()

def plot_latency_comparison(stats_df):
    """Create grouped bar plot for latency across patterns and strides"""
    # Filter only rows with latency data
    lat_df = stats_df[stats_df['Latency Mean (ns)'].notna()]
    
    if len(lat_df) == 0:
        print("No latency data available for plotting")
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    patterns = lat_df['Pattern'].unique()
    strides = sorted(lat_df['Stride (B)'].unique())
    
    x = np.arange(len(strides))
    width = 0.35
    
    for i, pattern in enumerate(patterns):
        pattern_data = lat_df[lat_df['Pattern'] == pattern]
        means = [pattern_data[pattern_data['Stride (B)'] == s]['Latency Mean (ns)'].values[0] 
                 if len(pattern_data[pattern_data['Stride (B)'] == s]) > 0 else 0 
                 for s in strides]
        stds = [pattern_data[pattern_data['Stride (B)'] == s]['Latency Std (ns)'].values[0] 
                if len(pattern_data[pattern_data['Stride (B)'] == s]) > 0 else 0 
                for s in strides]
        
        offset = width * (i - len(patterns)/2 + 0.5)
        bars = ax.bar(x + offset, means, width, yerr=stds, 
                     label=pattern.capitalize(), capsize=5, alpha=0.8)
        
        # Add value labels
        for bar, mean, std in zip(bars, means, stds):
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + std,
                       f'{mean:.0f}',
                       ha='center', va='bottom', fontsize=8)
    
    ax.set_xlabel('Stride (Bytes)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Latency (ns)', fontsize=12, fontweight='bold')
    ax.set_title('Experiment 2: Latency vs Stride and Pattern', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{s}B' for s in strides])
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plot_file = OUTPUT_DIR / "exp2_latency_comparison.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Latency plot saved to: {plot_file}")
    plt.close()

def plot_dual_axis(stats_df):
    """Create dual-axis plot showing both bandwidth and latency"""
    fig, ax1 = plt.subplots(figsize=(14, 7))
    
    patterns = stats_df['Pattern'].unique()
    strides = sorted(stats_df['Stride (B)'].unique())
    x = np.arange(len(patterns) * len(strides))
    
    # Prepare data
    labels = []
    bw_means = []
    lat_means = []
    
    for pattern in patterns:
        for stride in strides:
            row = stats_df[(stats_df['Pattern'] == pattern) & (stats_df['Stride (B)'] == stride)]
            if len(row) > 0:
                labels.append(f"{pattern[:3]}\n{stride}B")
                bw_means.append(row['BW Mean (MB/s)'].values[0])
                lat_means.append(row['Latency Mean (ns)'].values[0] if row['Latency Mean (ns)'].notna().values[0] else 0)
            else:
                labels.append(f"{pattern[:3]}\n{stride}B")
                bw_means.append(0)
                lat_means.append(0)
    
    # Plot bandwidth on primary axis
    color = 'tab:blue'
    ax1.set_xlabel('Pattern & Stride', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Bandwidth (MB/s)', color=color, fontsize=12, fontweight='bold')
    bars1 = ax1.bar(x - 0.2, bw_means, 0.4, color=color, alpha=0.7, label='Bandwidth')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=0, ha='center', fontsize=9)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Plot latency on secondary axis
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Latency (ns)', color=color, fontsize=12, fontweight='bold')
    bars2 = ax2.bar(x + 0.2, lat_means, 0.4, color=color, alpha=0.7, label='Latency')
    ax2.tick_params(axis='y', labelcolor=color)
    
    # Title and legend
    plt.title('Experiment 2: Bandwidth & Latency by Pattern and Stride', 
             fontsize=14, fontweight='bold', pad=20)
    
    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=10)
    
    plt.tight_layout()
    plot_file = OUTPUT_DIR / "exp2_dual_axis.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Dual-axis plot saved to: {plot_file}")
    plt.close()

def create_summary_table(stats_df):
    """Create formatted summary table"""
    print("\n" + "="*90)
    print("EXPERIMENT 2: PATTERN & GRANULARITY SWEEP RESULTS")
    print("="*90)
    print(f"\n{'Pattern':<12} {'Stride':<10} {'Bandwidth (MB/s)':<20} {'Latency (ns)':<20}")
    print("-" * 90)
    
    for _, row in stats_df.iterrows():
        pattern = row['Pattern']
        stride = f"{row['Stride (B)']}B"
        
        if not pd.isna(row['BW Mean (MB/s)']):
            bw = f"{row['BW Mean (MB/s)']:.1f} ± {row['BW Std (MB/s)']:.1f}"
        else:
            bw = "N/A"
        
        if not pd.isna(row['Latency Mean (ns)']):
            lat = f"{row['Latency Mean (ns)']:.1f} ± {row['Latency Std (ns)']:.1f}"
        else:
            lat = "N/A"
        
        print(f"{pattern:<12} {stride:<10} {bw:<20} {lat:<20}")
    
    print("-" * 90)
    
    # Save to file
    table_file = OUTPUT_DIR / "exp2_summary_table.txt"
    with open(table_file, 'w') as f:
        f.write("="*90 + "\n")
        f.write("EXPERIMENT 2: PATTERN & GRANULARITY SWEEP RESULTS\n")
        f.write("="*90 + "\n\n")
        f.write(f"{'Pattern':<12} {'Stride':<10} {'Bandwidth (MB/s)':<20} {'Latency (ns)':<20}\n")
        f.write("-" * 90 + "\n")
        
        for _, row in stats_df.iterrows():
            pattern = row['Pattern']
            stride = f"{row['Stride (B)']}B"
            
            if not pd.isna(row['BW Mean (MB/s)']):
                bw = f"{row['BW Mean (MB/s)']:.1f} ± {row['BW Std (MB/s)']:.1f}"
            else:
                bw = "N/A"
            
            if not pd.isna(row['Latency Mean (ns)']):
                lat = f"{row['Latency Mean (ns)']:.1f} ± {row['Latency Std (ns)']:.1f}"
            else:
                lat = "N/A"
            
            f.write(f"{pattern:<12} {stride:<10} {bw:<20} {lat:<20}\n")
        
        f.write("-" * 90 + "\n")
    
    print(f"\nTable saved to: {table_file}")

def main():
    print("Analyzing Experiment 2: Pattern & Granularity Sweep")
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
    plot_latency_comparison(stats_df)
    plot_dual_axis(stats_df)
    
    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)
    print("\nGenerated files:")
    print("  - exp2_bandwidth_comparison.png")
    print("  - exp2_latency_comparison.png")
    print("  - exp2_dual_axis.png")
    print("  - exp2_summary_table.txt")

if __name__ == "__main__":
    main()
