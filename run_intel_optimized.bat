@echo off
setlocal enabledelayedexpansion
title OllamaOpt - Optimized Intel AI Launcher

set "MODEL=%~1"
set "FORCE_DEVICE=%~2"
if "%MODEL%"=="" set "MODEL=llama3.2:3b"

echo ================================================
echo  OllamaOpt - Multi-Tier Intel Accelerator
echo ================================================
echo Model Target: %MODEL%

REM 0. Smart Routing Analysis
set "SUGGESTED_TIER=NPU"
if /i "!FORCE_DEVICE!"=="--force-gpu" (
    echo [USER] Forcing GPU Accelerator...
    set "SUGGESTED_TIER=GPU"
    goto hardware_detect
)
if /i "!FORCE_DEVICE!"=="--force-npu" (
    echo [USER] Forcing NPU Accelerator...
    set "SUGGESTED_TIER=NPU"
    goto hardware_detect
)

echo [INFO] Analyzing model for optimal accelerator...
ollama show "%MODEL%" --modelfile > model_info.tmp 2>nul
if %errorlevel% NEQ 0 (
    echo [WARN] Could not analyze model via Ollama. Defaulting to NPU tier.
) else (
    findstr /i "3b" model_info.tmp >nul && set "SUGGESTED_TIER=NPU"
    findstr /i "1b" model_info.tmp >nul && set "SUGGESTED_TIER=NPU"
    findstr /i "7b" model_info.tmp >nul && set "SUGGESTED_TIER=GPU"
    findstr /i "8b" model_info.tmp >nul && set "SUGGESTED_TIER=GPU"
    findstr /i "9b" model_info.tmp >nul && set "SUGGESTED_TIER=GPU"
    findstr /i "14b" model_info.tmp >nul && set "SUGGESTED_TIER=GPU"
    del model_info.tmp
)
echo [SUGGEST] Optimal Device for %MODEL% is !SUGGESTED_TIER!
echo:

:hardware_detect

REM 1. Hardware Detection
echo [INFO] Detect environment...
powershell -ExecutionPolicy Bypass -File gpu_diagnostics.ps1 | findstr /i "MATCH" > cpu_gen.txt
if not exist cpu_gen.txt (
    set "CPU_GEN_MATCH="
) else (
    set /p CPU_GEN_MATCH=<cpu_gen.txt
    del cpu_gen.txt
)

set "IPEX_FLAG="
if defined CPU_GEN_MATCH (
    echo "!CPU_GEN_MATCH!" | findstr /i "Arrow Lake" >nul && set "IPEX_FLAG=IPEX_LLM_NPU_ARL=1"
    echo "!CPU_GEN_MATCH!" | findstr /i "Lunar Lake" >nul && set "IPEX_FLAG=IPEX_LLM_NPU_DISABLE_COMPILE_OPT=1"
    echo "!CPU_GEN_MATCH!" | findstr /i "Meteor Lake" >nul && set "IPEX_FLAG=IPEX_LLM_NPU_MTL=1"
)

if not "%IPEX_FLAG%"=="" (
    echo [OK] CPU Flag: %IPEX_FLAG%
    for /f "tokens=1,2 delims==" %%a in ("%IPEX_FLAG%") do set "%%a=%%b"
    goto npu_check
)

echo [WARN] Automatic CPU detection yielded no specific flag. 
echo        Defaulting to Arrow Lake ^(ARL^) for Ultra 7 2xx series...
set "IPEX_LLM_NPU_ARL=1"

:npu_check
if "!SUGGESTED_TIER!"=="GPU" (
    echo [SKIP] Routing to GPU for performance (Model > 3.2B).
    goto gpu_fallback
)
echo:
REM 2. Tier 1: NPU (Accelerated llama-cpp)
set "NPU_PATH=docs\utils\llama-cpp-ipex-llm-2.3.0b20250424-win-npu"
if not exist "%NPU_PATH%\llama-cli-npu.exe" (
    echo [SKIP] NPU Optimized build not found.
    goto gpu_fallback
)

echo [INFO] Tier 1: Attempting NPU Acceleration...
echo Searching for Ollama model blob...
powershell -ExecutionPolicy Bypass -File find_ollama_model.ps1 -ModelName "%MODEL%" 2>nul > model_path.txt
if not exist model_path.txt (
    set "BLOB_PATH="
) else (
    set /p BLOB_PATH=<model_path.txt
    del model_path.txt
)

if "%BLOB_PATH%"=="" (
    echo [SKIP] NPU can't locate this specific model as a GGUF blob.
    goto gpu_fallback
)

echo [SUCCESS] Found Ollama model at: !BLOB_PATH!
echo Starting NPU-Accelerated Conversation Mode...
echo (Type your message and press Enter. Use Ctrl+C to exit.)
pushd "%NPU_PATH%"
llama-cli-npu.exe -m "!BLOB_PATH!" --color -cnv
set "NPU_EXIT_CODE=%errorlevel%"
popd

if %NPU_EXIT_CODE% EQU 0 goto end
echo [WARN] NPU Engine failed (likely unsupported architecture).
echo        Falling back to GPU (Tier 2)...

:gpu_fallback
echo:
echo [INFO] Tier 2: Falling back to GPU (Vulkan)...
set "OLLAMA_VULKAN=1"
set "OLLAMA_NUM_GPU=999"
echo Setting OLLAMA_VULKAN=1
ollama run "%MODEL%"
goto end

:end
echo:
echo ================================================
echo  Execution Complete
echo ================================================
pause
