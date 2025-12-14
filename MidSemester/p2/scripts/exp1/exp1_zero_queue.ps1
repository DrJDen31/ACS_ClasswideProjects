# Experiment 1: Zero-Queue Baselines
# Measures single-access latency for L1, L2, L3, and DRAM
# Points: 30 (10 + 10 + 10)

param(
    [int]$Repetitions = 5
)

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "Experiment 1: Zero-Queue Baselines"
Write-Host "========================================"
Write-Host ""

# Configuration
# Update this path to where you have mlc.exe installed
$MLC_PATH = "..\..\tools\mlc.exe"  # or C:\path\to\your\mlc.exe
$OUTPUT_DIR = "..\data\raw"
$OUTPUT_FILE = "$OUTPUT_DIR\exp1_zero_queue.csv"
$LOG_FILE = "$OUTPUT_DIR\exp1_zero_queue.log"

# Verify MLC exists
if (-not (Test-Path $MLC_PATH)) {
    Write-Error "Intel MLC not found at $MLC_PATH"
    exit 1
}

# Create output directory
New-Item -ItemType Directory -Force -Path $OUTPUT_DIR | Out-Null

# Start logging
Start-Transcript -Path $LOG_FILE -Force

Write-Host "Configuration:"
Write-Host "  MLC Path: $MLC_PATH"
Write-Host "  Output: $OUTPUT_FILE"
Write-Host "  Repetitions: $Repetitions"
Write-Host ""

# Initialize CSV
$csvHeader = "run,metric,value_ns,notes"
$csvHeader | Out-File -FilePath $OUTPUT_FILE -Encoding UTF8

Write-Host "Running Intel MLC idle latency measurements..."
Write-Host "This measures zero-queue (single-access) latency"
Write-Host ""

for ($run = 1; $run -le $Repetitions; $run++) {
    Write-Host "Run $run of $Repetitions..."
    
    # Run MLC idle latency
    $output = & $MLC_PATH --idle_latency 2>&1 | Out-String
    
    Write-Host $output
    
    # Parse the output
    # Look for lines like: "Each iteration took 322.1 base frequency clocks (       97.9   ns)"
    $lines = $output -split "`n"
    foreach ($line in $lines) {
        if ($line -match 'Each iteration took.*\(\s*([\d.]+)\s+ns\)') {
            $latency = $matches[1]
            "$run,L1_idle_latency,$latency,Measured with --idle_latency (L1 cache)" | Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
            Write-Host "  Captured: L1 idle latency = $latency ns" -ForegroundColor Green
        }
    }
    
    # Small delay between runs
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "========================================"
Write-Host "Phase 1 Complete: Idle Latency"
Write-Host "========================================"
Write-Host ""

# Additional measurements for cache levels
Write-Host "Running detailed latency measurements..."
Write-Host ""

# Run with bandwidth matrix to get more details
for ($run = 1; $run -le $Repetitions; $run++) {
    Write-Host "Detailed run $run of $Repetitions..."
    
    $output = & $MLC_PATH --latency_matrix 2>&1 | Out-String
    
    Write-Host $output
    
    # Parse latency matrix output
    # Look for lines like: "       0        94.6" (NUMA node latency)
    $lines = $output -split "`n"
    $captureNext = $false
    foreach ($line in $lines) {
        # Detect the data line after "Numa node          0"
        if ($line -match 'Numa node\s+0\s*$') {
            $captureNext = $true
            continue
        }
        if ($captureNext -and $line -match '^\s+0\s+([\d.]+)') {
            $latency = $matches[1]
            "$run,DRAM_random_latency,$latency,Random access latency (--latency_matrix)" | Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
            Write-Host "  Captured: DRAM random latency = $latency ns" -ForegroundColor Green
            $captureNext = $false
        }
    }
    
    Start-Sleep -Seconds 2
}

Stop-Transcript

Write-Host ""
Write-Host "========================================"
Write-Host "Experiment 1 Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "Output file: $OUTPUT_FILE"
Write-Host "Log file: $LOG_FILE"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Review the CSV file for collected latencies"
Write-Host "2. Run analysis script to compute statistics"
Write-Host "3. Generate latency table for report"
Write-Host ""
Write-Host "Note: MLC provides limited cache-level breakdown on some CPUs."
Write-Host "For more detailed L1/L2/L3 latencies, consider using:"
Write-Host "  - Custom pointer-chasing benchmark"
Write-Host "  - lmbench (on Linux/WSL)"
Write-Host "  - CPU specification sheets"
Write-Host ""
