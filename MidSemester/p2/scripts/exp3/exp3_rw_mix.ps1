# Experiment 3: Read/Write Mix Sweep
# Tests DRAM bandwidth under different R/W ratios
# Points: 30 (10 + 10 + 10)

param(
    [int]$Repetitions = 3  # Reduced from 5 for faster runs
)

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "Experiment 3: Read/Write Mix Sweep (Fast Mode)"
Write-Host "========================================"
Write-Host ""

# Configuration
$MLC_PATH = "..\..\tools\mlc.exe"
$OUTPUT_DIR = "..\..\data\raw"
$OUTPUT_FILE = "$OUTPUT_DIR\exp3_rw_mix.csv"
$LOG_FILE = "$OUTPUT_DIR\exp3_rw_mix.log"

# R/W ratios to test with --loaded_latency
# Note: MLC supports -W2 and -W3, but not -W1 (it's invalid)
$ratios = @(
    @{Name="All Reads"; Flag="--loaded_latency"; Extra=""},
    @{Name="3:1 Read:Write"; Flag="--loaded_latency"; Extra="-W3"},
    @{Name="2:1 Read:Write"; Flag="--loaded_latency"; Extra="-W2"}
)

# Verify MLC exists
if (-not (Test-Path $MLC_PATH)) {
    Write-Error "Intel MLC not found at $MLC_PATH"
    exit 1
}

# Create output directory
New-Item -ItemType Directory -Force -Path $OUTPUT_DIR | Out-Null

# Start logging (stop any existing transcript first)
try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
Start-Transcript -Path $LOG_FILE -Force

Write-Host "Configuration:"
Write-Host "  MLC Path: $MLC_PATH"
Write-Host "  Output: $OUTPUT_FILE"
Write-Host "  Repetitions: $Repetitions"
Write-Host "  Ratios: All Reads, 3:1 R:W, 2:1 R:W, 1:1 R:W"
Write-Host "  Using --loaded_latency to test mixed R/W patterns"
Write-Host ""

# Initialize CSV
$csvHeader = "run,ratio,read_pct,write_pct,bandwidth_mbps,notes"
$csvHeader | Out-File -FilePath $OUTPUT_FILE -Encoding UTF8

Write-Host "Running Read/Write Mix Sweep..."
Write-Host "Total tests: $($ratios.Count * $Repetitions)"
Write-Host ""

$testNum = 0
$totalTests = $ratios.Count * $Repetitions

foreach ($ratio in $ratios) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Testing: $($ratio.Name)" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    # Determine R/W percentages
    switch ($ratio.Name) {
        "All Reads"       { $readPct = 100; $writePct = 0 }
        "3:1 Read:Write"  { $readPct = 75; $writePct = 25 }
        "2:1 Read:Write"  { $readPct = 67; $writePct = 33 }
        "1:1 Read:Write"  { $readPct = 50; $writePct = 50 }
    }
    
    for ($run = 1; $run -le $Repetitions; $run++) {
        $testNum++
        Write-Host "[$testNum/$totalTests] Run $run/$Repetitions - $($ratio.Name)"
        
        # Build command
        $cmd = "$MLC_PATH $($ratio.Flag)"
        if ($ratio.Extra) {
            $cmd += " $($ratio.Extra)"
        }
        
        Write-Host "  Command: $cmd"
        
        # Run MLC
        $output = Invoke-Expression "$cmd 2>&1" | Out-String
        Write-Host $output
        
        # Parse bandwidth from --loaded_latency output
        # Extract the peak bandwidth (typically from delay=00000 or nearby low delays)
        $bandwidths = @()
        $lines = $output -split "`n"
        foreach ($line in $lines) {
            # Match lines like: " 00000  450.22    25883.1"
            if ($line -match '^\s+\d{5}\s+[\d.]+\s+([\d.]+)') {
                $bw = [double]$matches[1]
                $bandwidths += $bw
            }
        }
        
        if ($bandwidths.Count -gt 0) {
            # Take the maximum bandwidth observed
            $bandwidth = ($bandwidths | Measure-Object -Maximum).Maximum
            Write-Host "  ✓ Captured peak: $bandwidth MB/s" -ForegroundColor Green
            "$run,$($ratio.Name),$readPct,$writePct,$bandwidth,Loaded latency test" | 
                Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
        } else {
            # Mixed R/W - look for the specific ratio line
            if ($ratio.Name -eq "70/30 R/W" -and $output -match '3:1 Reads-Writes\s*:\s*([\d.]+)') {
                $bandwidth = $matches[1]
                Write-Host "  ✓ Captured: $bandwidth MB/s" -ForegroundColor Green
                "$run,$($ratio.Name),$readPct,$writePct,$bandwidth,3:1 read/write mix" | 
                    Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
            } elseif ($ratio.Name -eq "50/50 R/W" -and $output -match '1:1 Reads-Writes\s*:\s*([\d.]+)') {
                $bandwidth = $matches[1]
                Write-Host "  ✓ Captured: $bandwidth MB/s" -ForegroundColor Green
                "$run,$($ratio.Name),$readPct,$writePct,$bandwidth,1:1 read/write mix" | 
                    Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
            }
        }
        
        # Delay between runs
        Start-Sleep -Seconds 2
    }
    
    Write-Host ""
}

Stop-Transcript

Write-Host ""
Write-Host "========================================"
Write-Host "Experiment 3 Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "Output file: $OUTPUT_FILE"
Write-Host "Log file: $LOG_FILE"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Review CSV file for bandwidth data"
Write-Host "2. Run: cd ..\..\analysis; python analyze_exp3.py"
Write-Host "3. Compare R/W mix performance"
Write-Host ""
Write-Host "Expected observations:"
Write-Host "  - Read bandwidth typically highest"
Write-Host "  - Write bandwidth affected by buffer/cache effects"
Write-Host "  - Mixed ratios show intermediate performance"
Write-Host ""
