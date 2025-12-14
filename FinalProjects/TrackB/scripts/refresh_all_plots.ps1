param(
    [switch]$WhatIf
)

# Refresh the subset of plots that are actually referenced in B2-Report.tex
# by copying the corresponding PNGs from experiment results/plots directories
# into report/plots.
#
# Usage (from Windows PowerShell):
#   cd ..\TrackB
#   .\scripts\refresh_all_plots.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Resolve-Path (Join-Path $scriptDir "..")

$sourceRoot = Join-Path $projectDir "experiments"
$destDir    = Join-Path $projectDir "report/plots"

if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
}

# Explicit list of plot files used in B2-Report.tex. These are assumed to be
# produced under experiments/*/results/plots with matching filenames.
$plotFiles = @(
    # Experiment 0
    'exp0_recall_search_qps.png',
    'exp0_build_search_time.png',
    # Experiment 1
    'exp1_recall_qps.png',
    'exp1_latency_percentiles.png',
    # Experiment 2
    'exp2_recall_effective_qps.png',
    'exp2_io_per_query_vs_cache.png',
    # Experiment 3
    'exp3_hit_rate_vs_policy.png',
    'exp3_effective_qps_vs_policy.png',
    # Experiment 4
    'exp4_reads_per_query_vs_cache_frac.png',
    'exp4_bytes_per_query_vs_cache_frac.png',
    'exp4_device_time_per_query_vs_cache_frac.png',
    # Experiment 5
    'exp5_effective_qps_vs_ssd_profile.png',
    'exp5_device_time_per_query_vs_ssd_profile.png',
    # Experiment 6
    'exp6_cost_vs_effective_qps.png',
    'exp6_annssd_cost_sweep.png',
    # Experiment 7
    'exp7_build_time_vs_num_vectors.png',
    'exp7_effective_qps_vs_num_vectors.png',
    # Experiment 8
    'exp8_recall_vs_effective_qps.png',
    'exp8_build_time_vs_num_vectors.png',
    # Experiment 9
    'exp9_synthetic_gaussian_recall_qps.png',
    # Experiment 10
    'exp10_qps_recall_vs_max_steps_P1.png',
    'exp10_qps_recall_vs_max_steps_P2.png',
    'exp10_qps_recall_vs_max_steps_P2_K128.png',
    'exp10_qps_recall_vs_max_steps_P4.png',
    'exp10_recall_vs_effective_qps_P1.png',
    'exp10_recall_vs_effective_qps_P2.png',
    'exp10_recall_vs_effective_qps_P4.png',
    # Experiment 11
    'exp11_effective_qps_vs_num_vectors.png',
    'exp11_effective_qps_vs_num_vectors_by_level.png',
    'exp11_level_vs_qps_device_time_nb20k.png',
    # Experiment 12
    'exp12_SIFT1M_recall_vs_effective_qps.png',
    'exp12_synthetic_gaussian_recall_vs_effective_qps.png'
)

foreach ($name in $plotFiles) {
    # Look for this file somewhere under experiments/*/results/plots.
    $matches = Get-ChildItem -Path $sourceRoot -Recurse -Filter $name |
        Where-Object { $_.FullName -like "*\results\plots\*" }

    if (-not $matches) {
        Write-Warning "Plot file '$name' not found under $sourceRoot"
        continue
    }

    # If multiple matches exist (e.g., quick vs full runs), copy the first.
    $src = $matches[0]
    $destPath = Join-Path $destDir $name

    if ($WhatIf) {
        Write-Host "[WhatIf] Copy $($src.FullName) -> $destPath"
    }
    else {
        Write-Host "Copying $($src.FullName) -> $destPath"
        Copy-Item -Path $src.FullName -Destination $destPath -Force
    }
}

Write-Host "Refreshed" $plotFiles.Count "plots into" $destDir
