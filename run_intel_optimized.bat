@echo off
setlocal enabledelayedexpansion
title OllamaOpt - Optimized Intel AI Launcher

set MODEL=%~1
if "%MODEL%"=="" set MODEL=deepseek-r1:7b

echo ================================================
echo  OllamaOpt - Multi-Tier Intel Accelerator
echo ================================================
echo Model Target: %MODEL%
echo(

REM 1. Hardware Detection
echo [INFO] Detect environment...
powershell -ExecutionPolicy Bypass -File gpu_diagnostics.ps1 | findstr /i "MATCH" > cpu_gen.txt
set /p CPU_GEN_MATCH=<cpu_gen.txt
del cpu_gen.txt

set IPEX_FLAG=
if /i "%CPU_GEN_MATCH%"=="*Arrow Lake*" set IPEX_FLAG=IPEX_LLM_NPU_ARL=1
if /i "%CPU_GEN_MATCH%"=="*Lunar Lake*" set IPEX_FLAG=IPEX_LLM_NPU_DISABLE_COMPILE_OPT=1
if /i "%CPU_GEN_MATCH%"=="*Meteor Lake*" set IPEX_FLAG=IPEX_LLM_NPU_MTL=1

REM Default for Ultra 7 2xxU if detection fails but known to be Arrow Lake
if "%IPEX_FLAG%"=="" (
    echo [WARN] Automatic CPU detection yielded no specific flag. 
    echo        Defaulting to Arrow Lake (ARL) for Ultra 7 2xx series...
    set IPEX_LLM_NPU_ARL=1
) else (
    echo [OK] CPU Flag: %IPEX_FLAG%
    set %IPEX_FLAG%
)

echo(

REM 2. Tier 1: NPU (Accelerated llama-cpp)
set NPU_PATH=docs\utils\llama-cpp-ipex-llm-2.3.0b20250424-win-npu
if exist "%NPU_PATH%\llama-cli-npu.exe" (
    echo [INFO] Tier 1: Attempting NPU Acceleration...
    
    echo Searching for Ollama model blob...
    for /f "tokens=*" %%i in ('powershell -ExecutionPolicy Bypass -File find_ollama_model.ps1 -ModelName %MODEL% 2^>nul') do set BLOB_PATH=%%i
    
    if defined BLOB_PATH (
        echo [SUCCESS] Found Ollama model at: !BLOB_PATH!
        echo Starting NPU Engine...
        pushd "%NPU_PATH%"
        llama-cli-npu.exe -m "!BLOB_PATH!" -n 128 --prompt "Hi, how are you today?"
        popd
        goto end
    ) else (
        echo [SKIP] NPU can't locate this specific model as a GGUF blob.
    )
) else (
    echo [SKIP] NPU Optimized build not found.
)

REM 3. Tier 2: GPU (Vulkan Fallback)
echo(
echo [INFO] Tier 2: Falling back to GPU (Vulkan)...
set OLLAMA_VULKAN=1
set OLLAMA_NUM_GPU=999
echo Setting OLLAMA_VULKAN=1
ollama run %MODEL%
goto end

:end
echo(
echo ================================================
echo  Execution Complete
echo ================================================
pause
