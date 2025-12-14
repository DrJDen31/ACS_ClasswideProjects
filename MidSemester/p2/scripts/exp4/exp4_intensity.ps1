# Experiment 4: Intensity Sweep (Throughput-Latency Trade-off)
# Demonstrates queuing effects and identifies the knee point
# Points: 60 (20 + 15 + 15 + 10) - HIGHEST VALUE

param(
    [int]$Repetitions = 3
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Magenta
Write-Host "Experiment 4: Intensity Sweep" -ForegroundColor Magenta
Write-Host "HIGHEST VALUE: 60 points" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""

# Configuration
$MLC_PATH = "..\..\tools\mlc.exe"
$OUTPUT_DIR = "..\..\data\raw"
$OUTPUT_FILE = "$OUTPUT_DIR\exp4_intensity.csv"
$LOG_FILE = "$OUTPUT_DIR\exp4_intensity.log"

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
Write-Host ""
Write-Host "This experiment measures throughput-latency trade-off"
Write-Host "as memory system load increases (injection rate sweep)"
Write-Host ""

# Initialize CSV
$csvHeader = "run,injection_delay,latency_ns,bandwidth_mbps,concurrency,notes"
$csvHeader | Out-File -FilePath $OUTPUT_FILE -Encoding UTF8

Write-Host "Running Intensity Sweep..."
Write-Host "This will take several minutes per run"
Write-Host ""

for ($run = 1; $run -le $Repetitions; $run++) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Run $run of $Repetitions" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    # Run MLC loaded latency test
    $output = & $MLC_PATH --loaded_latency 2>&1 | Out-String
    
    Write-Host $output
    
    # Parse the output
    $lines = $output -split "`n"
    $inTable = $false
    
    foreach ($line in $lines) {
        # Detect start of data table
        if ($line -match '={10,}') {
            $inTable = $true
            continue
        }
        
        # Parse data lines with regex - more strict pattern
        if ($inTable -and $line -match '^\s*(\d{5})\s+([\d.]+)\s+([\d.]+)\s*$') {
            $delay = [int]$matches[1]
            $latency = [double]$matches[2]
            $bandwidth = [double]$matches[3]
            
            # Calculate concurrency approximation
            $concurrency = ($bandwidth * $latency) / 1000000
            
            "$run,$delay,$latency,$bandwidth,$concurrency,Loaded latency sweep" | 
                Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
            
            Write-Host "  Delay=$delay : Latency=$latency ns, BW=$bandwidth MB/s" -ForegroundColor Green
        }
        
        # Stop at cache-to-cache section
        if ($line -match 'cache-to-cache') {
            break
        }
    }
    
    Write-Host ""
    
    # Delay between runs
    if ($run -lt $Repetitions) {
        Start-Sleep -Seconds 5
    }
}

Stop-Transcript

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Experiment 4 Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Output file: $OUTPUT_FILE"
Write-Host "Log file: $LOG_FILE"
Write-Host ""
Write-Host "Critical Analysis Steps:" -ForegroundColor Yellow
Write-Host "1. Identify the knee point on throughput-latency curve" -ForegroundColor Yellow
Write-Host "2. Calculate percent of theoretical peak bandwidth" -ForegroundColor Yellow
Write-Host "3. Apply Littles Law to validate results" -ForegroundColor Yellow
Write-Host "4. Discuss diminishing returns beyond knee" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next step: cd ..\..\analysis; python analyze_exp4.py"
Write-Host ""
