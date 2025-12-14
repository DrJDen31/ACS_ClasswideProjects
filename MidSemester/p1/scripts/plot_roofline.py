#!/usr/bin/env python3
"""
Roofline Plot Generator for P1 SIMD Analysis
Plots measured kernel performance against theoretical roofline model
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import argparse
from pathlib import Path


def calculate_arithmetic_intensity(kernel_name):
    """
    Calculate arithmetic intensity (FLOPs per byte) for each kernel
    
    Kernel characteristics:
    - SAXPY: y = a*x + y  -> 2 FLOPs, 3 reads + 1 write = 4*sizeof(float) bytes
    - DOT: sum(x*y)       -> 2 FLOPs per element, 2 reads = 2*sizeof(float) bytes
    - MUL: z = x*y        -> 1 FLOP, 2 reads + 1 write = 3*sizeof(float) bytes
    - STENCIL: 3-pt       -> ~4 FLOPs, ~3 reads + 1 write = 4*sizeof(float) bytes
    """
    intensities = {
        'saxpy': {
            'f32': 2.0 / (4 * 4),  # 2 FLOPs / 16 bytes = 0.125
            'f64': 2.0 / (4 * 8),  # 2 FLOPs / 32 bytes = 0.0625
        },
        'dot': {
            'f32': 2.0 / (2 * 4),  # 2 FLOPs / 8 bytes = 0.25
            'f64': 2.0 / (2 * 8),  # 2 FLOPs / 16 bytes = 0.125
        },
        'mul': {
            'f32': 1.0 / (3 * 4),  # 1 FLOP / 12 bytes = 0.083
            'f64': 1.0 / (3 * 8),  # 1 FLOP / 24 bytes = 0.042
        },
        'stencil': {
            'f32': 4.0 / (4 * 4),  # 4 FLOPs / 16 bytes = 0.25
            'f64': 4.0 / (4 * 8),  # 4 FLOPs / 32 bytes = 0.125
        }
    }
    return intensities.get(kernel_name, {'f32': 0.1, 'f64': 0.05})


def create_roofline_plot(csv_files, output_path, peak_gflops=None, stream_bw_gbs=None):
    """
    Create roofline model plot with measured kernel performance
    
    Args:
        csv_files: List of paths to P1 CSV files
        output_path: Where to save the plot
        peak_gflops: Theoretical peak GFLOP/s (scalar and vector)
        stream_bw_gbs: Measured STREAM bandwidth in GB/s
    """
    
    # Default values if not provided
    if peak_gflops is None:
        peak_gflops = {
            'scalar_f32': 8.0,   # Adjust based on your CPU
            'scalar_f64': 4.0,
            'vector_f32': 64.0,  # AVX2: 8 FLOPs/cycle * 8 lanes
            'vector_f64': 32.0,
        }
    
    if stream_bw_gbs is None:
        stream_bw_gbs = {'f32': 40.0, 'f64': 40.0}  # Adjust based on STREAM results
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot roofline ceilings
    intensity_range = np.logspace(-2, 2, 100)  # 0.01 to 100 FLOPs/byte
    
    # Memory bandwidth ceilings (diagonal lines)
    for dtype in ['f32', 'f64']:
        bw = stream_bw_gbs.get(dtype, 40.0)
        perf_bw = intensity_range * bw
        label = f'Memory BW Ceiling ({dtype}): {bw:.1f} GB/s'
        ax.plot(intensity_range, perf_bw, '--', linewidth=2, label=label, alpha=0.7)
    
    # Compute ceilings (horizontal lines)
    for name, peak in peak_gflops.items():
        ax.axhline(y=peak, linestyle=':', linewidth=2, label=f'Peak {name}: {peak:.1f} GFLOP/s', alpha=0.7)
    
    # Plot measured kernel performance
    colors = {'saxpy': 'red', 'dot': 'blue', 'mul': 'green', 'stencil': 'purple'}
    markers = {'scalar': 'o', 'auto': 's', 'avx2': '^'}
    
    for csv_file in csv_files:
        if not Path(csv_file).exists():
            print(f"Warning: {csv_file} not found, skipping")
            continue
        
        # Extract kernel name from filename
        kernel = Path(csv_file).stem.replace('p1_', '').replace('_stride', '')
        if kernel not in colors:
            continue
        
        df = pd.read_csv(csv_file)
        
        # Filter: only large N (bandwidth-limited), aligned, stride=1
        df_filtered = df[df['n'] >= 2**20]  # Large working sets
        if 'misaligned' in df.columns:
            df_filtered = df_filtered[df_filtered['misaligned'] == 0]
        if 'stride' in df.columns:
            df_filtered = df_filtered[df_filtered['stride'] == 1]
        
        intensities = calculate_arithmetic_intensity(kernel)
        
        for dtype in ['f32', 'f64']:
            for variant in ['scalar', 'auto', 'avx2']:
                subset = df_filtered[
                    (df_filtered['dtype'] == dtype) &
                    (df_filtered['variant'].str.contains(variant))
                ]
                
                if subset.empty:
                    continue
                
                # Use peak performance for this kernel
                peak_perf = subset['gflops'].max()
                intensity = intensities[dtype]
                
                label = f'{kernel}_{variant}_{dtype}'
                ax.scatter(intensity, peak_perf, 
                          c=colors[kernel], marker=markers[variant], 
                          s=150, alpha=0.8, edgecolors='black', linewidth=1.5,
                          label=label)
    
    # Formatting
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Arithmetic Intensity (FLOPs/Byte)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Performance (GFLOP/s)', fontsize=14, fontweight='bold')
    ax.set_title('Roofline Model: P1 SIMD Kernels', fontsize=16, fontweight='bold')
    ax.grid(True, which='both', alpha=0.3, linestyle='--')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Roofline plot saved to {output_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Generate roofline plot for P1 kernels')
    parser.add_argument('--data_dir', default='data/raw', help='Directory containing P1 CSV files')
    parser.add_argument('--out', default='plots/p1/roofline.png', help='Output plot path')
    parser.add_argument('--peak_scalar_f32', type=float, default=8.0, help='Peak scalar f32 GFLOP/s')
    parser.add_argument('--peak_scalar_f64', type=float, default=4.0, help='Peak scalar f64 GFLOP/s')
    parser.add_argument('--peak_vector_f32', type=float, default=64.0, help='Peak vector f32 GFLOP/s')
    parser.add_argument('--peak_vector_f64', type=float, default=32.0, help='Peak vector f64 GFLOP/s')
    parser.add_argument('--stream_bw', type=float, default=40.0, help='STREAM bandwidth in GB/s')
    
    args = parser.parse_args()
    
    # Find all P1 CSV files (non-stride)
    data_dir = Path(args.data_dir)
    csv_files = [
        data_dir / 'p1_saxpy.csv',
        data_dir / 'p1_dot.csv',
        data_dir / 'p1_mul.csv',
        data_dir / 'p1_stencil.csv',
    ]
    
    peak_gflops = {
        'scalar_f32': args.peak_scalar_f32,
        'scalar_f64': args.peak_scalar_f64,
        'vector_f32': args.peak_vector_f32,
        'vector_f64': args.peak_vector_f64,
    }
    
    stream_bw = {'f32': args.stream_bw, 'f64': args.stream_bw}
    
    # Create output directory
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    
    create_roofline_plot(csv_files, args.out, peak_gflops, stream_bw)


if __name__ == '__main__':
    main()
