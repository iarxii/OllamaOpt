@echo off
setlocal enabledelayedexpansion
title OllamaOpt - Optimized Intel AI Launcher

set "MODEL=%~1"
set "FORCE_DEVICE=%~2"
if "%MODEL%"=="" set "MODEL=llama3.2:3b"

echo ================================================
echo  OllamaOpt - Multi-Tier Intel Accelerator
echo ================================================
echo Model Target: "%MODEL%"

REM -------------------------------------------------------------------
REM 0. Smart Routing Analysis
REM -------------------------------------------------------------------
set "SUGGESTED_TIER=NPU"

if /i "%FORCE_DEVICE%"=="--force-gpu" (
    echo [USER] Forcing GPU Accelerator...
    set "SUGGESTED_TIER=GPU"
    goto hardware_detect
)
if /i "%FORCE_DEVICE%"=="--force-npu" (
    echo [USER] Forcing NPU Accelerator...
    set "SUGGESTED_TIER=NPU"
    goto hardware_detect
)

echo [INFO] Analyzing model for optimal accelerator...

REM Check the model name directly first for common sizes
echo "%MODEL%" | findstr /i "3b 1b 1.5b" >nul && (
    set "SUGGESTED_TIER=NPU"
    goto tier_confirmed
)
echo "%MODEL%" | findstr /i "7b 8b 9b 11b 14b" >nul && (
    set "SUGGESTED_TIER=GPU"
    goto tier_confirmed
)

REM Fallback to modelfile analysis if name is ambiguous
ollama show "%MODEL%" --modelfile > model_info.tmp 2>nul
if %errorlevel% NEQ 0 (
    echo [WARN] Could not analyze model via Ollama. Defaulting to NPU tier.
    goto tier_confirmed
)

REM Only check the top of the modelfile to avoid matching license text
set /p FIRST_LINE=<model_info.tmp
echo "!FIRST_LINE!" | findstr /i "7b 8b 9b 14b" >nul && set "SUGGESTED_TIER=GPU"
if exist model_info.tmp del model_info.tmp

:tier_confirmed
echo [SUGGEST] Optimal Device for "%MODEL%" is "%SUGGESTED_TIER%"
echo:

:hardware_detect
REM -------------------------------------------------------------------
REM 1. Hardware Detection (Safe Environment)
REM -------------------------------------------------------------------
echo [INFO] Detect environment...

set "CPU_NAME="
REM Use -NoProfile to avoid failures from OneDrive-based user scripts
for /f "usebackq tokens=*" %%a in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-CimInstance Win32_Processor).Name"`) do (
    set "CPU_NAME=%%a"
)

if "%CPU_NAME%"=="" (
    echo [WARN] Pro hardware detection failed. Defaulting to Meteor Lake...
    set "IPEX_LLM_NPU_MTL=1"
    goto tier_check
)

echo [OK] CPU Detected: "%CPU_NAME%"

set "IPEX_FLAG="
REM Regex-style matches for Intel generations
echo "%CPU_NAME%" | findstr /i "Ultra" >nul || goto no_ultra

echo "%CPU_NAME%" | findstr /r "2..V" >nul && set "IPEX_FLAG=IPEX_LLM_NPU_DISABLE_COMPILE_OPT=1"
echo "%CPU_NAME%" | findstr /r "2..H 2..U" >nul && set "IPEX_FLAG=IPEX_LLM_NPU_ARL=1"
echo "%CPU_NAME%" | findstr /r "1..H 1..U" >nul && set "IPEX_FLAG=IPEX_LLM_NPU_MTL=1"

:no_ultra
if "%IPEX_FLAG%"=="" (
    echo [INFO] Standard Intel CPU. Using Arrow Lake defaults for best compatibility...
    set "IPEX_LLM_NPU_ARL=1"
    goto tier_check
)

echo [OK] Accelerator Flag: "%IPEX_FLAG%"
for /f "tokens=1,2 delims==" %%a in ("%IPEX_FLAG%") do set "%%a=%%b"

:tier_check
if "%SUGGESTED_TIER%"=="GPU" (
    echo [SKIP] Routing to GPU for performance ^(Model ^> 3.2B^).
    goto gpu_fallback
)

echo:
REM -------------------------------------------------------------------
REM 2. Tier 1: NPU (Accelerated llama-cpp)
REM -------------------------------------------------------------------
set "NPU_PATH=docs\utils\llama-cpp-ipex-llm-2.3.0b20250424-win-npu"
if not exist "%NPU_PATH%\llama-cli-npu.exe" (
    echo [SKIP] NPU Optimized build not found.
    goto gpu_fallback
)

echo [INFO] Tier 1: Attempting NPU Acceleration...
echo Searching for Ollama model blob...
powershell -NoProfile -ExecutionPolicy Bypass -File find_ollama_model.ps1 -ModelName "%MODEL%" 2>nul > model_path.txt

set "BLOB_PATH="
if exist model_path.txt (
    set /p BLOB_PATH=<model_path.txt
    del model_path.txt
)

if "%BLOB_PATH%"=="" (
    echo [SKIP] NPU can't locate this specific model as a GGUF blob.
    goto gpu_fallback
)

echo [SUCCESS] Found Ollama model at: "!BLOB_PATH!"
echo Starting NPU-Accelerated Conversation Mode...
echo (Type your message and press Enter. Use Ctrl+C to exit.)
pushd "%NPU_PATH%"
REM -i -if mode silences the "Are you sure?" prompt and provides a clean chat experience.
REM Added -r tokens to prevent hallucinations.
llama-cli-npu.exe -m "%BLOB_PATH%" --color -i -if -p "You are a helpful AI assistant." --in-prefix "User: " --in-suffix "Assistant: " -r "<|eot_id|>" -r "<|eom_id|>" -r "User:" -n 512 --temp 0.1 --simple-io
popd
goto end

:gpu_fallback
echo:
REM -------------------------------------------------------------------
REM 3. Tier 2: GPU (Vulkan Fallback)
REM -------------------------------------------------------------------
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
