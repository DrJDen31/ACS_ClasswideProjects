# Simple Setup Check Script for Project 2

Write-Host "========================================"
Write-Host "Project 2 - Environment Check"
Write-Host "========================================"
Write-Host ""

# CPU Information
Write-Host "CPU Information:"
$cpu = Get-WmiObject Win32_Processor
Write-Host "  Name: $($cpu.Name)"
Write-Host "  Cores: $($cpu.NumberOfCores)"
Write-Host "  Logical Processors: $($cpu.NumberOfLogicalProcessors)"
Write-Host "  Max Clock Speed: $($cpu.MaxClockSpeed) MHz"
Write-Host "  L2 Cache: $($cpu.L2CacheSize) KB"
Write-Host "  L3 Cache: $($cpu.L3CacheSize) KB"
Write-Host ""

# Memory Information
Write-Host "Memory Information:"
$memory = Get-WmiObject Win32_PhysicalMemory
$totalMemoryGB = ($memory | Measure-Object -Property Capacity -Sum).Sum / 1GB
Write-Host "  Total Memory: $([math]::Round($totalMemoryGB, 2)) GB"
Write-Host "  Modules: $($memory.Count)"
Write-Host ""

# Check for Intel MLC
Write-Host "Intel MLC Check:"
if (Test-Path "..\tools\mlc.exe") {
    Write-Host "  [OK] Intel MLC found" -ForegroundColor Green
} else {
    Write-Host "  [MISSING] Intel MLC not found" -ForegroundColor Red
    Write-Host "  Download from: https://www.intel.com/content/www/us/en/download/736633/" -ForegroundColor Yellow
}
Write-Host ""

# Check for WSL
Write-Host "WSL Check:"
if (Get-Command wsl -ErrorAction SilentlyContinue) {
    Write-Host "  [OK] WSL is installed" -ForegroundColor Green
    wsl --list --verbose
} else {
    Write-Host "  [MISSING] WSL not found" -ForegroundColor Red
    Write-Host "  Required for Linux perf experiments" -ForegroundColor Yellow
}
Write-Host ""

# Check for Python
Write-Host "Python Check:"
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonVersion = python --version
    Write-Host "  [OK] $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  [MISSING] Python not found" -ForegroundColor Red
}
Write-Host ""

# Check Python packages
Write-Host "Python Packages:"
$packages = @("numpy", "matplotlib", "pandas")
foreach ($pkg in $packages) {
    try {
        python -c "import $pkg" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] $pkg installed" -ForegroundColor Green
        } else {
            Write-Host "  [MISSING] $pkg" -ForegroundColor Red
        }
    } catch {
        Write-Host "  [MISSING] $pkg" -ForegroundColor Red
    }
}
Write-Host ""

# Power Plan
Write-Host "Power Configuration:"
$activePlan = powercfg /getactivescheme
Write-Host "  $activePlan"
Write-Host ""

# Directory Check
Write-Host "Directory Structure:"
$dirs = @("scripts", "data\raw", "plots", "src", "analysis", "tools")
foreach ($dir in $dirs) {
    $fullPath = "..\$dir"
    if (Test-Path $fullPath) {
        Write-Host "  [OK] $dir" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $dir" -ForegroundColor Yellow
        New-Item -ItemType Directory -Force -Path $fullPath | Out-Null
        Write-Host "       Created $dir" -ForegroundColor Cyan
    }
}
Write-Host ""

Write-Host "========================================"
Write-Host "Setup check complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Download Intel MLC to p2\tools\ directory"
Write-Host "2. Install Python packages: pip install numpy matplotlib pandas"
Write-Host "3. Run: .\collect_system_info.ps1"
Write-Host ""
