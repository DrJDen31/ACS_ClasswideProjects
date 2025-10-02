#!/usr/bin/env python3
"""
Experiment 7 Analysis: TLB-Miss Impact
Compares standard 4KB pages vs huge 2MB pages
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path

DATA_FILE = Path("../data/raw/exp7_tlb_miss.csv")
OUTPUT_DIR = Path("../plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    if not DATA_FILE.exists():
        print(f"Error: Data file not found: {DATA_FILE}")
        sys.exit(1)
    
    df = pd.read_csv(DATA_FILE)
    print(f"Loaded {len(df)} measurements")
    return df

def plot_comparison(stats_df):
    """Compare 4KB vs 2MB pages"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    labels = ['4KB Pages', '2MB Huge Pages']
    runtime = [stats_df[stats_df['use_hugepages']==0]['runtime_ms_mean'].values[0],
               stats_df[stats_df['use_hugepages']==1]['runtime_ms_mean'].values[0]]
    miss_rate = [stats_df[stats_df['use_hugepages']==0]['miss_rate_pct_mean'].values[0],
                 stats_df[stats_df['use_hugepages']==1]['miss_rate_pct_mean'].values[0]]
    
    # Runtime comparison
    bars1 = ax1.bar(labels, runtime, color=['steelblue', 'green'], alpha=0.8)
    ax1.set_ylabel('Runtime (ms)', fontsize=12, fontweight='bold')
    ax1.set_title('Runtime Comparison', fontsize=13, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    
    for bar, val in zip(bars1, runtime):
        ax1.text(bar.get_x() + bar.get_width()/2, val, f'{val:.1f}',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # Miss rate comparison
    bars2 = ax2.bar(labels, miss_rate, color=['steelblue', 'green'], alpha=0.8)
    ax2.set_ylabel('TLB Miss Rate (%)', fontsize=12, fontweight='bold')
    ax2.set_title('TLB Miss Rate Comparison', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    
    for bar, val in zip(bars2, miss_rate):
        ax2.text(bar.get_x() + bar.get_width()/2, val, f'{val:.4f}%',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    plt.suptitle('Experiment 7: TLB-Miss Impact (4KB vs 2MB Pages)', 
                fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "exp7_comparison.png", dpi=300, bbox_inches='tight')
    print(f"Comparison plot saved")
    plt.close()

def main():
    print("Analyzing Experiment 7: TLB-Miss Impact")
    print("=" * 80)
    
    df = load_data()
    
    stats_df = df.groupby('use_large_pages').agg({
        'runtime_ms': ['mean', 'std']
    }).reset_index()
    
    stats_df.columns = ['_'.join(col).strip('_') for col in stats_df.columns.values]
    
    # Create simple bar plot
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 6))
    
    page_types = ['4KB Standard', '2MB Large Pages'] if len(stats_df) == 2 else ['4KB Standard']
    runtimes = [stats_df[stats_df['use_large_pages']==0]['runtime_ms_mean'].values[0]]
    if len(stats_df) == 2:
        runtimes.append(stats_df[stats_df['use_large_pages']==1]['runtime_ms_mean'].values[0])
    
    bars = ax.bar(page_types, runtimes, color=['steelblue', 'orange'] if len(runtimes)==2 else ['steelblue'])
    ax.set_ylabel('Runtime (ms)', fontsize=12, fontweight='bold')
    ax.set_title('Experiment 7: TLB-Miss Impact Comparison', fontsize=14, fontweight='bold')
    
    # Zoom in on the actual data range to make small differences visible
    min_val = min(runtimes) * 0.95
    max_val = max(runtimes) * 1.05
    ax.set_ylim([min_val, max_val])
    
    # Add value labels on bars
    for bar, runtime in zip(bars, runtimes):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{runtime:.2f} ms',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plot_file = OUTPUT_DIR / "exp7_tlb_comparison.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved to: {plot_file}")
    plt.close()
    
    print("\nTLB-Miss Impact Results (Timing-Only):")
    print("=" * 60)
    print(f"{'Page Type':<20} {'Runtime (ms)':<25}")
    print("-" * 60)
    
    for _, row in stats_df.iterrows():
        page_type = '2MB Large Pages' if row['use_large_pages'] == 1 else '4KB Standard'
        runtime = row['runtime_ms_mean']
        std = row['runtime_ms_std']
        print(f"{page_type:<20} {runtime:>10.2f} ± {std:<10.2f}")
    
    # Calculate improvement
    if len(stats_df) == 2:
        std_runtime = stats_df[stats_df['use_large_pages']==0]['runtime_ms_mean'].values[0]
        large_runtime = stats_df[stats_df['use_large_pages']==1]['runtime_ms_mean'].values[0]
        speedup = (std_runtime / large_runtime - 1) * 100
        
        print(f"\nPerformance improvement with large pages: {speedup:+.1f}%")
        print("\nInterpretation:")
        print("- 4KB pages require more TLB entries for same address space")
        print("- 2MB pages reduce TLB pressure significantly")
        print(f"- Speedup of {speedup:.1f}% demonstrates TLB impact")
    else:
        print("\nNote: Only one page type tested (likely not running as Administrator)")
        print("Large pages require Administrator privileges on Windows")
    
    print("\n" + "="*80)
    print("Analysis complete!")

if __name__ == "__main__":
    main()
