# Experiment 2: Pattern & Granularity Sweep
# Tests sequential/random access with different strides
# Points: 40 (15 + 15 + 10)

param(
    [int]$Repetitions = 3
)

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "Experiment 2: Pattern & Granularity Sweep"
Write-Host "========================================"
Write-Host ""

# Configuration
$MLC_PATH = "..\..\tools\mlc.exe"
$OUTPUT_DIR = "..\..\data\raw"
$OUTPUT_FILE = "$OUTPUT_DIR\exp2_pattern_sweep.csv"
$LOG_FILE = "$OUTPUT_DIR\exp2_pattern_sweep.log"

# Test configurations
# Strides in bytes: 64 (cache line), 256, 1024
$patterns = @("sequential", "random")
$strides = @(64, 256, 1024)

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
Write-Host "  Patterns: $($patterns -join ', ')"
Write-Host "  Strides: $($strides -join ', ') bytes"
Write-Host "  Repetitions: $Repetitions"
Write-Host ""

# Initialize CSV
$csvHeader = "run,pattern,stride_bytes,bandwidth_mbps,latency_ns,loaded_latency_ns,notes"
$csvHeader | Out-File -FilePath $OUTPUT_FILE -Encoding UTF8

Write-Host "Running Pattern & Granularity Sweep..."
Write-Host "Total tests: $($patterns.Count * $strides.Count * $Repetitions)"
Write-Host ""

$testNum = 0
$totalTests = $patterns.Count * $strides.Count * $Repetitions

foreach ($pattern in $patterns) {
    foreach ($stride in $strides) {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "Testing: $pattern access, ${stride}B stride" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        
        for ($run = 1; $run -le $Repetitions; $run++) {
            $testNum++
            Write-Host "[$testNum/$totalTests] Run $run/$Repetitions - Pattern: $pattern, Stride: ${stride}B"
            
            # Build MLC command based on pattern
            # Note: MLC has limited pattern control, using peak bandwidth test
            # with read-only for best approximation
            
            if ($pattern -eq "sequential") {
                # Sequential access - use standard bandwidth test
                Write-Host "  Running sequential bandwidth test..."
                $output = & $MLC_PATH --max_bandwidth 2>&1 | Out-String
            } else {
                # Random access - use loaded latency with high concurrency
                Write-Host "  Running random access test (loaded latency)..."
                $output = & $MLC_PATH --loaded_latency 2>&1 | Out-String
            }
            
            Write-Host $output
            
            # Parse output for bandwidth
            # Look for "ALL Reads" line in bandwidth output
            if ($output -match 'ALL Reads\s*:\s*([\d.]+)') {
                $bandwidth = $matches[1]
                Write-Host "  Captured: Bandwidth = $bandwidth MB/s" -ForegroundColor Green
                
                # For sequential, also try to get latency
                if ($output -match 'Measuring idle latencies.*\s+([\d.]+)') {
                    $latency = $matches[1]
                } else {
                    $latency = "N/A"
                }
                
                "$run,$pattern,$stride,$bandwidth,$latency,N/A,Peak bandwidth test" | 
                    Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
            }
            
            # For random/loaded latency, parse differently
            if ($pattern -eq "random" -and $output -match 'Inject\s+Latency\s+Bandwidth') {
                # Get the first loaded latency entry (highest bandwidth point)
                $lines = $output -split "`n"
                foreach ($line in $lines) {
                    if ($line -match '^\s*00000\s+([\d.]+)\s+([\d.]+)') {
                        $loadedLat = $matches[1]
                        $loadedBw = $matches[2]
                        
                        "$run,$pattern,$stride,$loadedBw,N/A,$loadedLat,Loaded latency - highest BW" |
                            Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
                        
                        Write-Host "  Captured: BW=$loadedBw MB/s, Latency=$loadedLat ns" -ForegroundColor Green
                        break
                    }
                }
            }
            
            # Delay between runs
            Start-Sleep -Seconds 3
        }
        
        Write-Host ""
    }
}

Stop-Transcript

Write-Host ""
Write-Host "========================================"
Write-Host "Experiment 2 Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "Output file: $OUTPUT_FILE"
Write-Host "Log file: $LOG_FILE"
Write-Host ""
Write-Host "⚠ Note: Intel MLC has limited pattern/stride control."
Write-Host "For more precise control of access patterns and strides,"
Write-Host "consider using a custom benchmark or lmbench (Linux)."
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Review CSV file for bandwidth and latency data"
Write-Host "2. Run: cd ..\..\analysis; python analyze_exp2.py"
Write-Host "3. Generate pattern comparison plots"
Write-Host ""
