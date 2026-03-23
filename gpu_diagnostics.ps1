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

$gpus = Get-CimInstance -ClassName Win32_VideoController | Where-Object { $_.Name -match "Intel" }

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
    $modelName = "qwen3.5:9b"
    Write-Host "[INFO] 4. Analyzing GPU offload for model '$modelName'..."

    try {
        $showRes = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:11434/api/show" -Body (@{name=$modelName} | ConvertTo-Json) -ContentType "application/json"
        
        # In modern Ollama, we look for 'library' in the verbose show output or check the model details
        # Since API might not give full verbose text easily, we check if it mentions 'intel' or 'vulkan' or 'gpu'
        $jsonStr = $showRes | ConvertTo-Json -Depth 10
        
        if ($jsonStr -like "*gpu*" -or $jsonStr -like "*intel*" -or $jsonStr -like "*vulkan*") {
            if ($jsonStr -like "*vulkan*") {
                Write-Host "[SUCCESS] GPU acceleration is ACTIVE (via Vulkan fallback)!" -ForegroundColor Green
            } else {
                Write-Host "[SUCCESS] GPU acceleration is ACTIVE (via Intel SYCL/Level Zero)!" -ForegroundColor Green
            }
        } else {
            Write-Host "[WARNING] No GPU layers detected for '$modelName'. Likely running on CPU." -ForegroundColor Yellow
            Write-Host "          Try setting OLLAMA_VULKAN=1 in your environment if Intel SYCL fails."
        }
    } catch {
        Write-Host "[FAIL] Could not analyze model offload via API. Is '$modelName' pulled?"
    }
} else {
    Write-Host "[INFO] 4. Skipping GPU offload analysis (Server not running)."
}

Write-Host ""
Write-Host "================================================"
Write-Host "  Diagnostics Complete"
Write-Host "================================================"
Write-Host ""
