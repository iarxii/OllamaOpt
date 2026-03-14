$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "================================================"
Write-Host "  OllamaOpt - GPU Diagnostics"
Write-Host "================================================"
Write-Host ""

# 1) Check Intel GPU devices
Write-Host "[INFO] Checking for Intel GPU devices..."

$gpus = Get-WmiObject -Class Win32_VideoController | Where-Object { $_.Name -match "Intel" }

if ($gpus) {
    Write-Host "[OK] Intel GPU(s) detected:"
    foreach ($gpu in $gpus) {
        Write-Host "  - $($gpu.Name)"
        Write-Host "    Driver Version: $($gpu.DriverVersion)"
        Write-Host "    Status: $($gpu.Status)"
    }
} else {
    Write-Host "[WARN] No Intel GPU detected!"
    Write-Host "  Available GPUs:"
    Get-WmiObject -Class Win32_VideoController | ForEach-Object {
        Write-Host "      - $($_.Name)"
    }
}

Write-Host ""

# 2) Environment variables
Write-Host "[INFO] Current Intel GPU environment variables:"
Write-Host "  OLLAMA_NUM_GPU=$($env:OLLAMA_NUM_GPU)"
Write-Host "  ZES_ENABLE_SYSMAN=$($env:ZES_ENABLE_SYSMAN)"
Write-Host "  SYCL_CACHE_PERSISTENT=$($env:SYCL_CACHE_PERSISTENT)"
Write-Host "  OLLAMA_DEBUG=$($env:OLLAMA_DEBUG)"

Write-Host ""

# 3) Test Ollama detection
Write-Host "[INFO] Testing Ollama configuration..."

try {
    $version = & ollama -v
    Write-Host "[OK] Ollama version: $version"
} catch {
    Write-Host "[FAIL] Ollama not found in PATH"
}

Write-Host ""

# 4) Check if model exists and try to get info
Write-Host "[INFO] Checking for qwen3.5:9b model..."

try {
    $models = & ollama list
    if ($models -match "qwen3.5:9b") {
        Write-Host "[OK] qwen3.5:9b is installed"
        Write-Host ""
        Write-Host "[INFO] Model info (checking GPU offload status):"
        Write-Host "  Run this command manually to see if GPU layers are allocated:"
        Write-Host "    ollama show qwen3.5:9b"
    } else {
        Write-Host "[WARN] qwen3.5:9b not found"
        Write-Host "  Available models:"
        $models | Where-Object { $_ -match "^[a-z]" }
    }
} catch {
    Write-Host "[FAIL] Could not query Ollama"
}

Write-Host ""
Write-Host "================================================"
Write-Host "  Diagnostics Complete"
Write-Host "================================================"
Write-Host ""
Write-Host "Next Steps:"
Write-Host "  1) If no Intel GPU found: Install Intel Arc drivers from intel.com"
Write-Host "  2) If GPU found but old driver: Update Intel GPU drivers"
Write-Host "  3) Run: ollama show qwen3.5:9b"
Write-Host "  4) Look for GPU layer offload info in the output"
Write-Host ""
