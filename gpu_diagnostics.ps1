$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "================================================"
Write-Host "  OllamaOpt - GPU Diagnostics"
Write-Host "================================================"
Write-Host ""

# -------------------------------------------------------------------
# 0) Check if Ollama server is running
# -------------------------------------------------------------------
Write-Host "[INFO] Checking for running Ollama server on port 11434..."
$serverCheck = Test-NetConnection -ComputerName localhost -Port 11434 -ErrorAction SilentlyContinue
if ($serverCheck.TcpTestSucceeded) {
    Write-Host "[OK] Ollama server is responding."
} else {
    Write-Host "[FAIL] Ollama server is not responding on port 11434." -ForegroundColor Red
    Write-Host "  Please start the server first by running 'start_dev.bat' in another terminal."
    Write-Host "  This script can only analyze a running server."
    Write-Host ""
    exit 1
}

Write-Host ""

# -------------------------------------------------------------------
# 1) Check Intel GPU devices
# -------------------------------------------------------------------
Write-Host "[INFO] 1. Checking for Intel GPU devices..."

$gpus = Get-WmiObject -Class Win32_VideoController | Where-Object { $_.Name -match "Intel" }

if ($gpus) {
    Write-Host "[OK] Intel GPU(s) detected:"
    foreach ($gpu in $gpus) {
        Write-Host "  - $($gpu.Name)"
        Write-Host "    Driver Version: $($gpu.DriverVersion)"
        $DriverDate = [Management.ManagementDateTimeConverter]::ToDateTime($gpu.DriverDate)
        Write-Host "    Driver Date:    $($DriverDate.ToString('yyyy-MM-dd'))"
        Write-Host "    Status:         $($gpu.Status)"
    }
} else {
    Write-Host "[WARN] No Intel GPU detected!"
    Write-Host "  Available GPUs:"
    Get-WmiObject -Class Win32_VideoController | ForEach-Object {
        Write-Host "      - $($_.Name)"
    }
}

Write-Host ""

# -------------------------------------------------------------------
# 2) Check for Critical Intel Driver Libraries
# -------------------------------------------------------------------
Write-Host "[INFO] 2. Checking for critical driver libraries..."

$sycl_support = "NOT FOUND"
$level_zero_support = "NOT FOUND"

$sycl_path = Join-Path $env:SystemRoot "System32\igcsycl.dll"
$level_zero_path = Join-Path $env:SystemRoot "System32\ze_intel_gpu.dll"

if (Test-Path $sycl_path) {
    $sycl_support = "OK"
}
if (Test-Path $level_zero_path) {
    $level_zero_support = "OK"
}

Write-Host "  - SYCL support (igcsycl.dll):      $sycl_support"
Write-Host "  - Level Zero support (ze_intel_gpu.dll): $level_zero_support"

if ($sycl_support -ne "OK" -or $level_zero_support -ne "OK") {
    Write-Host "[FAIL] Critical Intel compute libraries are missing." -ForegroundColor Red
    Write-Host "  This indicates an incomplete or incorrect driver installation."
    Write-Host "  A full driver reinstall using the Intel DSA is highly recommended."
} else {
    Write-Host "[OK] Critical Intel compute libraries found."
}

Write-Host ""

# -------------------------------------------------------------------
# 3) Test Ollama detection
# -------------------------------------------------------------------
Write-Host "[INFO] 3. Testing Ollama CLI..."

try {
    $version = & ollama -v
    Write-Host "[OK] Ollama version: $version"
} catch {
    Write-Host "[FAIL] Ollama not found in PATH"
}

Write-Host ""

# -------------------------------------------------------------------
# 4) Check Model and Analyze GPU Offload
# -------------------------------------------------------------------
$modelName = "qwen:0.5b" # A smaller model for faster checks
Write-Host "[INFO] 4. Checking for '$modelName' model and analyzing offload..."

try {
    $models = & ollama list
    if ($models -match $modelName) {
        Write-Host "[OK] $modelName is installed"
        Write-Host ""
        Write-Host "[INFO] Analyzing model layers for GPU offload (this may take a moment)..."

        # Run 'ollama show' and capture the output
        $showOutput = & ollama show $modelName --verbose

        # Check for GPU layers
        $gpuLayers = $showOutput | Select-String -Pattern "library: intel" -AllMatches
        $cpuLayers = $showOutput | Select-String -Pattern "library: cpu" -AllMatches

        $totalGpuLayers = if ($gpuLayers) { $gpuLayers.Matches.Count } else { 0 }
        $totalCpuLayers = if ($cpuLayers) { $cpuLayers.Matches.Count } else { 0 }
        
        if ($totalGpuLayers -gt 0) {
            Write-Host "[PASS] GPU offload is ACTIVE!" -ForegroundColor Green
            Write-Host "  - $totalGpuLayers layers detected on Intel GPU."
            if ($totalCpuLayers -gt 0) {
                Write-Host "  - $totalCpuLayers layers are on CPU (this may be normal for some layers)." -ForegroundColor Yellow
            }
        } else {
            Write-Host "[FAIL] GPU offload is NOT working." -ForegroundColor Red
            Write-Host "  - All $totalCpuLayers layers appear to be running on the CPU."
            Write-Host "  - This is likely a GPU driver issue. Please install the latest drivers from intel.com."
            Write-Host "  - The installed driver may not support the necessary compute features (Level Zero / SYCL)."
        }
    } else {
        Write-Host "[WARN] $modelName not found. You can pull it by running: ollama pull $modelName"
        Write-Host "  Available models:"
        $models | Where-Object { $_ -match "^[a-z]" }
    }
} catch {
    Write-Host "[FAIL] Could not query Ollama. Is the server running?" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================================"
Write-Host "  Diagnostics Complete"
Write-Host "================================================"
Write-Host ""

if ($sycl_support -ne "OK" -or $level_zero_support -ne "OK" -or $totalGpuLayers -eq 0) {
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Update your Intel GPU drivers to the LATEST version."
    Write-Host "     The best way is to use the Intel Driver & Support Assistant (DSA)."
    Write-Host "     Download it from: https://www.intel.com/content/www/us/en/support/detect.html"
    Write-Host "  2. Perform a CLEAN installation of the drivers. This often involves"
    Write-Host "     uninstalling the old driver first via Windows Apps & Features."
    Write-Host "  3. After installing the new drivers and rebooting, run 'start_clean.bat' and then 'start_dev.bat'."
    Write-Host "  4. Rerun this diagnostic script to verify the fix."
}
