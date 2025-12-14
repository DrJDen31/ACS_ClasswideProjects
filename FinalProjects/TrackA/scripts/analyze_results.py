#!/usr/bin/env python3
"""
Analysis script for Project A4 benchmark results
Parses CSV data and generates statistics
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

def load_results(csv_file):
    """Load benchmark results from CSV"""
    df = pd.read_csv(csv_file)
    
    # Filter out failed runs
    df = df[df['throughput_ops_sec'] != 'FAILED']
    df['throughput_ops_sec'] = df['throughput_ops_sec'].astype(float)
    
    # Convert to Mops/sec for readability
    df['throughput_mops_sec'] = df['throughput_ops_sec'] / 1e6
    
    return df

def compute_statistics(df):
    """Compute statistics across repetitions"""
    stats = df.groupby(['strategy', 'workload', 'threads', 'dataset_size']).agg({
        'throughput_mops_sec': ['median', 'mean', 'std', 'min', 'max', 'count']
    }).reset_index()
    
    # Flatten column names
    stats.columns = ['strategy', 'workload', 'threads', 'dataset_size', 
                     'median', 'mean', 'std', 'min', 'max', 'count']
    
    return stats

def compute_speedup(stats):
    """Compute speedup relative to 1-thread baseline"""
    speedup_data = []
    
    for (strategy, workload, size), group in stats.groupby(['strategy', 'workload', 'dataset_size']):
        # Get baseline (1 thread)
        baseline = group[group['threads'] == 1]['median'].values
        
        if len(baseline) == 0:
            continue
        
        baseline = baseline[0]
        
        for _, row in group.iterrows():
            speedup = row['median'] / baseline
            speedup_data.append({
                'strategy': strategy,
                'workload': workload,
                'dataset_size': size,
                'threads': row['threads'],
                'throughput': row['median'],
                'speedup': speedup
            })
    
    return pd.DataFrame(speedup_data)

def print_summary(stats):
    """Print summary tables"""
    print("\n" + "="*80)
    print("BENCHMARK RESULTS SUMMARY")
    print("="*80)
    
    for workload in stats['workload'].unique():
        print(f"\n{'='*80}")
        print(f"Workload: {workload.upper()}")
        print(f"{'='*80}")
        
        wl_data = stats[stats['workload'] == workload]
        
        for size in sorted(wl_data['dataset_size'].unique()):
            size_data = wl_data[wl_data['dataset_size'] == size]
            
            print(f"\nDataset Size: {size:,} keys")
            print(f"{'-'*80}")
            print(f"{'Strategy':<10} {'Threads':>7} {'Median':>12} {'Mean':>12} {'Std':>10} {'Min':>12} {'Max':>12}")
            print(f"{'-'*80}")
            
            for _, row in size_data.sort_values(['strategy', 'threads']).iterrows():
                print(f"{row['strategy']:<10} {row['threads']:7d} "
                      f"{row['median']:12.2f} {row['mean']:12.2f} {row['std']:10.2f} "
                      f"{row['min']:12.2f} {row['max']:12.2f}")

def print_speedup_table(speedup_df):
    """Print speedup analysis"""
    print("\n" + "="*80)
    print("SPEEDUP ANALYSIS (relative to 1 thread)")
    print("="*80)
    
    for workload in speedup_df['workload'].unique():
        print(f"\n{'='*80}")
        print(f"Workload: {workload.upper()}")
        print(f"{'='*80}")
        
        wl_data = speedup_df[speedup_df['workload'] == workload]
        
        for size in sorted(wl_data['dataset_size'].unique()):
            size_data = wl_data[wl_data['dataset_size'] == size]
            
            print(f"\nDataset Size: {size:,} keys")
            print(f"{'-'*80}")
            print(f"{'Strategy':<10} {'Threads':>7} {'Throughput':>12} {'Speedup':>10} {'Efficiency':>10}")
            print(f"{'-'*80}")
            
            for _, row in size_data.sort_values(['strategy', 'threads']).iterrows():
                efficiency = (row['speedup'] / row['threads']) * 100
                print(f"{row['strategy']:<10} {row['threads']:7d} "
                      f"{row['throughput']:12.2f} {row['speedup']:10.2f}x {efficiency:9.1f}%")

def save_tables(stats, speedup_df, output_dir):
    """Save tables as CSV"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    stats.to_csv(output_dir / 'statistics.csv', index=False)
    speedup_df.to_csv(output_dir / 'speedup.csv', index=False)
    
    print(f"\nTables saved to {output_dir}/")

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_results.py <results.csv>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '../results/analysis'
    
    print(f"Loading results from: {csv_file}")
    df = load_results(csv_file)
    
    print(f"Loaded {len(df)} data points")
    print(f"Configurations: {len(df.groupby(['strategy', 'workload', 'threads', 'dataset_size']))}")
    
    print("\nComputing statistics...")
    stats = compute_statistics(df)
    
    print("Computing speedup...")
    speedup_df = compute_speedup(stats)
    
    print_summary(stats)
    print_speedup_table(speedup_df)
    save_tables(stats, speedup_df, output_dir)
    
    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)

if __name__ == '__main__':
    main()
