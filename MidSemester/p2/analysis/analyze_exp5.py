#!/usr/bin/env python3
"""
Experiment 5 Analysis: Working-Set Size Sweep
Shows locality transitions through cache hierarchy
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path

# Configuration
DATA_FILE = Path("../data/raw/exp5_working_set.csv")
OUTPUT_DIR = Path("../plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Expected cache sizes (KB) - from Exp 1 or system config
L1_SIZE = 32
L2_SIZE = 512
L3_SIZE = 16384

def load_data():
    """Load experiment data"""
    if not DATA_FILE.exists():
        print(f"Error: Data file not found: {DATA_FILE}")
        sys.exit(1)
    
    df = pd.read_csv(DATA_FILE)
    print(f"Loaded {len(df)} measurements")
    return df

def compute_statistics(df):
    """Compute statistics grouped by working set size"""
    stats = df.groupby('working_set_kb').agg({
        'runtime_ms': ['mean', 'std'],
        'bandwidth_mbps': ['mean', 'std']
    }).reset_index()
    
    stats.columns = ['_'.join(col).strip('_') for col in stats.columns.values]
    return stats

def plot_locality_transitions(stats_df):
    """Create annotated plot showing cache level transitions"""
    fig, ax = plt.subplots(figsize=(14, 8))
    
    x = stats_df['working_set_kb'].values
    y = stats_df['runtime_ms_mean'].values
    yerr = stats_df['runtime_ms_std'].values
    
    # Plot with log scale on x-axis
    ax.errorbar(x, y, yerr=yerr, fmt='o-', markersize=8, capsize=4, 
                linewidth=2, color='steelblue', label='Measured Runtime')
    
    # Add vertical lines for cache boundaries
    ax.axvline(x=L1_SIZE, color='green', linestyle='--', linewidth=2, alpha=0.7, label=f'L1 Size ({L1_SIZE} KB)')
    ax.axvline(x=L2_SIZE, color='orange', linestyle='--', linewidth=2, alpha=0.7, label=f'L2 Size ({L2_SIZE} KB)')
    ax.axvline(x=L3_SIZE, color='red', linestyle='--', linewidth=2, alpha=0.7, label=f'L3 Size ({L3_SIZE} MB)')
    
    # Annotate regions
    ax.text(L1_SIZE/2, ax.get_ylim()[1]*0.9, 'L1\nRegion', ha='center', fontsize=11, fontweight='bold', color='green')
    ax.text(np.sqrt(L1_SIZE*L2_SIZE), ax.get_ylim()[1]*0.9, 'L2\nRegion', ha='center', fontsize=11, fontweight='bold', color='orange')
    ax.text(np.sqrt(L2_SIZE*L3_SIZE), ax.get_ylim()[1]*0.9, 'L3\nRegion', ha='center', fontsize=11, fontweight='bold', color='darkorange')
    ax.text(L3_SIZE*2, ax.get_ylim()[1]*0.9, 'DRAM\nRegion', ha='center', fontsize=11, fontweight='bold', color='red')
    
    ax.set_xlabel('Working Set Size (KB)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Runtime (ms)', fontsize=13, fontweight='bold')
    ax.set_title('Experiment 5: Locality Transitions Through Cache Hierarchy', fontsize=14, fontweight='bold')
    ax.set_xscale('log')
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(True, alpha=0.3, which='both', linestyle='--')
    
    plt.tight_layout()
    plot_file = OUTPUT_DIR / "exp5_locality_transitions.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {plot_file}")
    plt.close()

def main():
    print("Analyzing Experiment 5: Working-Set Size Sweep")
    print("=" * 80)
    
    df = load_data()
    stats_df = compute_statistics(df)
    
    print("\nWorking-Set Size vs Runtime:")
    print("=" * 70)
    print(f"{'Size (KB)':<12} {'Runtime (ms)':<25} {'Bandwidth (MB/s)':<20} {'Level'}")
    print("-" * 70)
    
    for _, row in stats_df.iterrows():
        size = row['working_set_kb']
        runtime = row['runtime_ms_mean']
        runtime_std = row['runtime_ms_std']
        bw = row['bandwidth_mbps_mean']
        
        level = ("L1" if size < L1_SIZE else 
                "L2" if size < L2_SIZE else 
                "L3" if size < L3_SIZE else "DRAM")
        
        print(f"{size:<12} {runtime:>8.2f} ± {runtime_std:<8.2f}   {bw:>10.1f}          {level}")
    
    plot_locality_transitions(stats_df)
    
    print("\n" + "="*80)
    print("Analysis complete!")
    print("Look for performance drops at cache boundaries")

if __name__ == "__main__":
    main()
