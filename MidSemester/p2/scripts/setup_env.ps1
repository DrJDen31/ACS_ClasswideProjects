# Project 2 Environment Setup Script (Windows PowerShell)
# This script checks for required tools and displays system information

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Project 2 Environment Setup (Windows)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$issues = 0

function Write-Success {
    param([string]$Message)
    Write-Host "[✓] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[⚠] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[✗] $Message" -ForegroundColor Red
    $script:issues++
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

# Check system information
Write-Section "System Information"
$computerInfo = Get-ComputerInfo -Property @('CsName', 'OsName', 'OsVersion', 'OsArchitecture')
Write-Host "Computer Name: $($computerInfo.CsName)"
Write-Host "OS: $($computerInfo.OsName)"
Write-Host "Version: $($computerInfo.OsVersion)"
Write-Host "Architecture: $($computerInfo.OsArchitecture)"

# Check CPU information
Write-Section "CPU Information"
$cpu = Get-WmiObject Win32_Processor
Write-Host "Name: $($cpu.Name)"
Write-Host "Manufacturer: $($cpu.Manufacturer)"
Write-Host "Architecture: $($cpu.Architecture)"
Write-Host "Max Clock Speed: $($cpu.MaxClockSpeed) MHz"
Write-Host "Number of Cores: $($cpu.NumberOfCores)"
Write-Host "Number of Logical Processors: $($cpu.NumberOfLogicalProcessors)"
Write-Host "L2 Cache Size: $($cpu.L2CacheSize) KB"
Write-Host "L3 Cache Size: $($cpu.L3CacheSize) KB"

# Check memory information
Write-Section "Memory Configuration"
$memory = Get-WmiObject Win32_PhysicalMemory
$totalMemoryGB = ($memory | Measure-Object -Property Capacity -Sum).Sum / 1GB
Write-Host "Total Memory: $([math]::Round($totalMemoryGB, 2)) GB"
Write-Host ""
Write-Host "Memory Modules:"
foreach ($mem in $memory) {
    $capacityGB = $mem.Capacity / 1GB
    $memSpeed = $mem.Speed
    Write-Host "  - $capacityGB GB at $memSpeed MHz"
}

# Check cache line size
Write-Section "Cache Configuration"
$cacheInfo = Get-WmiObject Win32_CacheMemory
foreach ($cache in $cacheInfo) {
    $sizeKB = $cache.InstalledSize
    $level = $cache.Level
    $type = $cache.CacheType
    Write-Host "Level $level Cache: $sizeKB KB (Type: $type)"
}

# Check for WSL
Write-Section "WSL Status"
if (Get-Command wsl -ErrorAction SilentlyContinue) {
    Write-Success "WSL is installed"
    try {
        $wslVersion = wsl --version 2>&1 | Select-Object -First 1
        Write-Host "  Version: $wslVersion"
        Write-Host ""
        Write-Host "  WSL distributions:"
        wsl --list --verbose
    } catch {
        Write-Host "  Could not get WSL version"
    }
} else {
    Write-Warning "WSL not found"
    Write-Host "  WSL is required for Linux perf tool"
    Write-Host "  Install from: https://aka.ms/wslinstall"
    $script:issues++
}

# Check for Intel MLC
Write-Section "Intel MLC"
$mlcPath = "..\tools\mlc.exe"
if (Test-Path $mlcPath) {
    Write-Success "Intel MLC found at $mlcPath"
} else {
    Write-Error "Intel MLC not found at $mlcPath"
    Write-Host "  Download from: https://www.intel.com/content/www/us/en/download/736633/intel-memory-latency-checker-intel-mlc.html"
    Write-Host "  Extract mlc.exe to: p2\tools\"
}

# Check for Python
Write-Section "Python Environment"
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonVersion = python --version
    Write-Success "Python found: $pythonVersion"
    
    # Check Python packages
    Write-Host ""
    Write-Host "Checking Python packages..."
    $packages = @("numpy", "matplotlib", "pandas")
    foreach ($pkg in $packages) {
        try {
            python -c "import $pkg" 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Success "$pkg installed"
            } else {
                Write-Error "$pkg not installed"
                Write-Host "  Install with: pip install $pkg"
            }
        } catch {
            Write-Error "$pkg not installed"
            Write-Host "  Install with: pip install $pkg"
        }
    }
} else {
    Write-Error "Python not found"
    Write-Host "  Install from: https://www.python.org/downloads/"
}

# Check for CMake
Write-Section "Build Tools"
if (Get-Command cmake -ErrorAction SilentlyContinue) {
    $cmakeVersion = cmake --version | Select-Object -First 1
    Write-Success "CMake found: $cmakeVersion"
} else {
    Write-Warning "CMake not found"
    Write-Host "  Install from: https://cmake.org/download/"
    Write-Host "  Or use: winget install Kitware.CMake"
}

# Check for compiler
if (Get-Command gcc -ErrorAction SilentlyContinue) {
    $gccVersion = gcc --version | Select-Object -First 1
    Write-Success "GCC found: $gccVersion"
} elseif (Get-Command cl -ErrorAction SilentlyContinue) {
    Write-Success "MSVC compiler found"
} else {
    Write-Warning "No C++ compiler found"
    Write-Host "  Install Visual Studio or MinGW-w64"
}

# Check power plan
Write-Section "Power Configuration"
$activePlan = powercfg /getactivescheme
Write-Host "Active Power Plan:"
Write-Host "  $activePlan"
if ($activePlan -match "High performance") {
    Write-Success "High performance power plan active"
} else {
    Write-Warning "Not using High Performance power plan"
    Write-Host "  Recommended: Switch to High Performance for consistent results"
    Write-Host "  Run: powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
}

# Directory structure check
Write-Section "Directory Structure"
$dirs = @("scripts", "data\raw", "plots", "src", "analysis", "tools")
foreach ($dir in $dirs) {
    $fullPath = "..\$dir"
    if (Test-Path $fullPath) {
        Write-Success "$dir exists"
    } else {
        Write-Warning "$dir missing"
        New-Item -ItemType Directory -Force -Path $fullPath | Out-Null
        Write-Host "  Created directory: $dir"
    }
}

# Summary
Write-Section "Setup Summary"
if ($issues -eq 0) {
    Write-Success "All checks passed!"
    Write-Host "System is ready for Project 2 experiments." -ForegroundColor Green
} else {
    Write-Warning "Found $issues issue(s)"
    Write-Host "Please address the issues above before running experiments." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Complete SYSTEM_CONFIG.md with your system details"
Write-Host "2. Download Intel MLC if not present (place in p2\tools\)"
Write-Host "3. Install WSL for Linux perf access"
Write-Host "4. Set power plan to High Performance"
Write-Host "5. Install Python packages: pip install numpy matplotlib pandas"
Write-Host "6. Run system info collection script"
Write-Host ""
Write-Host "For Linux perf experiments, run setup_env.sh in WSL:"
Write-Host "  wsl -e bash scripts/setup_env.sh"
Write-Host ""
