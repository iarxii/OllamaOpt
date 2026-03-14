$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "================================================"
Write-Host "  OllamaOpt - GPU Diagnostics"
Write-Host "================================================"
Write-Host ""

# 0) Check if Ollama server is running
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
Write-Host "[INFO] Environment variables in THIS shell:"
Write-Host "  NOTE: These may be empty. The important variables are set in the"
Write-Host "  'Ollama Server' terminal window when you run 'start_dev.bat'."

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
$modelName = "qwen3.5:9b"
Write-Host "[INFO] Checking for $modelName model..."

try {
    $models = & ollama list
    if ($models -match $modelName) {
        Write-Host "[OK] $modelName is installed"
        Write-Host ""
        Write-Host "[INFO] Analyzing model layers for GPU offload..."

        # Run 'ollama show' and capture the output
        $showOutput = & ollama show $modelName --verbose

        # Check for GPU layers
        $gpuLayers = $showOutput | Select-String -Pattern "library: intel" -AllMatches
        $cpuLayers = $showOutput | Select-String -Pattern "library: cpu" -AllMatches

        if ($gpuLayers.Matches.Count -gt 0) {
            Write-Host "[PASS] GPU offload is working!" -ForegroundColor Green
            Write-Host "  - $($gpuLayers.Matches.Count) layers detected on Intel GPU."
            if ($cpuLayers.Matches.Count -gt 0) {
                Write-Host "  - $($cpuLayers.Matches.Count) layers are on CPU (this may be normal for some layers)." -ForegroundColor Yellow
            }
        } else {
            Write-Host "[FAIL] GPU offload is NOT working." -ForegroundColor Red
            Write-Host "  - All layers appear to be running on the CPU."
            Write-Host "  - This is likely a GPU driver issue. Please install the latest drivers from intel.com."
            Write-Host "  - This is almost always a GPU driver issue. The installed driver may not support"
            Write-Host "    the necessary compute features (Level Zero / SYCL)."
        }
    } else {
        Write-Host "[WARN] $modelName not found"
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

if ($gpuLayers.Matches.Count -eq 0) {
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Update your Intel GPU drivers."
    Write-Host "     The best way is to use the Intel Driver & Support Assistant."
    Write-Host "     Download it from: https://www.intel.com/content/www/us/en/support/detect.html"
    Write-Host "  2. After installing the new drivers and rebooting, run 'start_clean.bat' and then 'start_dev.bat'."
    Write-Host "  3. Rerun this diagnostic script to verify the fix."
}
