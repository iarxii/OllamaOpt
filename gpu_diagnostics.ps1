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
$serverCheck = Test-NetConnection -ComputerName 127.0.0.1 -Port 11434 -ErrorAction SilentlyContinue
$apiUp = $serverCheck.TcpTestSucceeded

if ($apiUp) {
    Write-Host "[OK] Ollama server is responding at 127.0.0.1:11434"
} else {
    Write-Host "[WAIT] Ollama server is NOT responding at 127.0.0.1:11434" -ForegroundColor Yellow
    Write-Host "       Check if 'ollama serve' is running."
}

Write-Host ""

# -------------------------------------------------------------------
# 1) Check Intel GPU devices via WMI
# -------------------------------------------------------------------
Write-Host "[INFO] 1. Checking for Intel GPU devices..."

$gpus = Get-CimInstance -ClassName Win32_VideoController | Where-Object { $_.Name -match "Intel|Arc|Xe" }

if ($gpus) {
    Write-Host "[OK] Intel GPU(s) detected:"
    foreach ($gpu in $gpus) {
        Write-Host "  - $($gpu.Name)"
        Write-Host "    Driver Version: $($gpu.DriverVersion)"
        Write-Host "    Status:         $($gpu.Status)"
    }
} else {
    Write-Host "[WARN] No Intel GPU detected via standard WMI!"
}

Write-Host ""

# -------------------------------------------------------------------
# 1b) Check Intel NPU (AI Boost)
# -------------------------------------------------------------------
Write-Host "[INFO] 1b. Checking for Intel NPU (AI Boost)..."

$npu = Get-CimInstance -ClassName Win32_PnPEntity | Where-Object { $_.Name -match "Intel" -and ($_.Name -match "AI Boost" -or $_.HardwareID -match "NPU") }

if ($npu) {
    Write-Host "[OK] Intel NPU detected: $($npu.Name)"
    Write-Host "    Driver Version: $($npu.DriverVersion)"
    
    $reqVersion = "32.0.100.3104"
    if ([version]$npu.DriverVersion -ge [version]$reqVersion) {
        Write-Host "    [SUCCESS] NPU Driver is IPEX-LLM Ready (>= $reqVersion)" -ForegroundColor Green
    } else {
        Write-Host "    [WARNING] NPU Driver is below recommended $reqVersion for IPEX-LLM." -ForegroundColor Yellow
    }
} else {
    Write-Host "[FAIL] No Intel NPU detected. Optimized NPU offload will not be available." -ForegroundColor Red
}

Write-Host ""

# -------------------------------------------------------------------
# 1c) Detect CPU Generation for IPEX-LLM Flags
# -------------------------------------------------------------------
Write-Host "[INFO] 1c. Detecting CPU Generation for IPEX-LLM Flags..."
$cpuName = (Get-CimInstance Win32_Processor).Name
Write-Host "  - CPU: $cpuName"

$ipexFlags = ""
if ($cpuName -match "Ultra\s+(\d\s+)?([12]\d\d[VHKU])") {
    if ($cpuName -match "Ultra\s+(\d\s+)?2\d\d[V]") {
        Write-Host "    [MATCH] Lunar Lake (Series 2) detected." -ForegroundColor Cyan
        $ipexFlags = "IPEX_LLM_NPU_DISABLE_COMPILE_OPT=1"
    } elseif ($cpuName -match "Ultra\s+(\d\s+)?2\d\d[HKU]") {
        Write-Host "    [MATCH] Arrow Lake (Series 2) detected." -ForegroundColor Cyan
        $ipexFlags = "IPEX_LLM_NPU_ARL=1"
    } elseif ($cpuName -match "Ultra\s+(\d\s+)?1\d\d[H]") {
        Write-Host "    [MATCH] Meteor Lake (Series 1) detected." -ForegroundColor Cyan
        $ipexFlags = "IPEX_LLM_NPU_MTL=1"
    }
    Write-Host "    Recommended Flag: $ipexFlags"
} else {
    Write-Host "    [INFO] Standard Intel CPU detected. NPU features may be limited."
}

Write-Host ""

# -------------------------------------------------------------------
# 2) Search for Critical Intel compute libraries
# -------------------------------------------------------------------
Write-Host "[INFO] 2. Searching for Intel compute libraries..."
$libSycl = "igcsycl.dll"
$libLZero = "ze_intel_gpu.dll"

$commonPaths = @(
    "$env:SystemRoot\System32",
    "$env:SystemDrive\Windows\System32\DriverStore\FileRepository"
)

$foundSycl = $false
$foundLZero = $false

foreach ($path in $commonPaths) {
    if (Test-Path $path) {
        if (-not $foundSycl) {
            # Increasing depth to find drivers in deeper subfolders
            $check = Get-ChildItem -Path $path -Filter $libSycl -Recurse -Depth 3 -ErrorAction SilentlyContinue
            if ($check) { $foundSycl = $true; Write-Host "[OK]  $libSycl found in: $($check[0].DirectoryName)" }
        }
        if (-not $foundLZero) {
            $check = Get-ChildItem -Path $path -Filter $libLZero -Recurse -Depth 3 -ErrorAction SilentlyContinue
            if ($check) { $foundLZero = $true; Write-Host "[OK]  $libLZero found in: $($check[0].DirectoryName)" }
        }
    }
}

if (-not $foundSycl) { Write-Host "[FAIL] $libSycl NOT found (Required for Intel SYCL)" -ForegroundColor Red }
if (-not $foundLZero) { Write-Host "[FAIL] $libLZero NOT found (Required for Intel Level Zero)" -ForegroundColor Red }

Write-Host ""

# -------------------------------------------------------------------
# 3) Check Ollama installation and Vulkan
# -------------------------------------------------------------------
Write-Host "[INFO] 3. Testing Ollama CLI and Vulkan..."

try {
    $version = & ollama -v
    Write-Host "[OK] Ollama version: $version"
} catch {
    Write-Host "[FAIL] Ollama CLI not found."
}

$vulkanCheck = Get-Command vulkaninfo -ErrorAction SilentlyContinue
if ($vulkanCheck) {
    Write-Host "[OK] Vulkan support detected."
} else {
    Write-Host "[INFO] Vulkan utility not found (normal if not installed separately)."
}

Write-Host ""

# -------------------------------------------------------------------
# 4) Analyze GPU Offload via API
# -------------------------------------------------------------------
if ($apiUp) {
    Write-Host "[INFO] 4. Analyzing active GPU offload via API..."

    try {
        # Using /api/ps to see currently loaded models and their compute allocation
        $psRes = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:11434/api/ps"
        $jsonStr = $psRes | ConvertTo-Json -Depth 10
        
        # Check if any running model is using GPU (Vulkan, SYCL, or Generic GPU)
        if ($jsonStr -like "*gpu*" -or $jsonStr -like "*intel*" -or $jsonStr -like "*vulkan*") {
            Write-Host "[SUCCESS] GPU acceleration is ACTIVE!" -ForegroundColor Green
        } else {
            # Fallback check if no models are actively loaded in /api/ps
            # Check the /api/tags or /api/show as a hint for capability
            $showRes = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:11434/api/show" -Body (@{name="qwen3.5:9b"} | ConvertTo-Json) -ContentType "application/json"
            $jsonStrShow = $showRes | ConvertTo-Json -Depth 10
            
            if ($jsonStrShow -like "*gpu*" -or $jsonStrShow -like "*intel*" -or $jsonStrShow -like "*vulkan*") {
                 Write-Host "[SUCCESS] GPU acceleration is ACTIVE!" -ForegroundColor Green
            } else {
                Write-Host "[WARNING] No GPU layers detected. Likely running on CPU." -ForegroundColor Yellow
                Write-Host "          Try setting OLLAMA_VULKAN=1 in your environment if Intel SYCL fails."
            }
        }
    } catch {
        Write-Host "[FAIL] Could not analyze model offload via API."
    }
} else {
    Write-Host "[INFO] 4. Skipping GPU offload analysis (Server not running)."
}
# -------------------------------------------------------------------
# 5) Accelerator Memory & Utilization (NPU + iGPU)
# -------------------------------------------------------------------
Write-Host "[INFO] 5. Reporting Accelerator Performance..."

$gpuCounters = Get-Counter -Counter "\GPU Process Memory(*)\Local Usage" -ErrorAction SilentlyContinue
if ($gpuCounters) {
    $totalGpuMem = 0
    foreach ($sample in $gpuCounters.CounterSamples) {
        $totalGpuMem += $sample.CookedValue
    }
    $totalGpuMemMB = [math]::Round($totalGpuMem / 1MB, 2)
    Write-Host "  - iGPU Active Memory: $totalGpuMemMB MB"
}

$npuPerf = Get-Counter -Counter "\NPU(*)\Utilization Percentage" -ErrorAction SilentlyContinue
if ($npuPerf) {
    foreach ($sample in $npuPerf.CounterSamples) {
        $val = [math]::Round($sample.CookedValue, 2)
        Write-Host "  - NPU Utilization:    $val %"
    }
} else {
    Write-Host "  - NPU Utilization:    [N/A] (No active workload or driver counter hidden)"
}

Write-Host ""

Write-Host ""
Write-Host "================================================"
Write-Host "  Diagnostics Complete"
Write-Host "================================================"
Write-Host ""
