@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ================================================================
echo   OllamaOpt CLI  -  Local LLM Intel GPU Optimization
echo ================================================================
echo.

REM ================================================================
REM  Step 1 -- Logging setup
REM ================================================================
echo [Step 1/6] Setting up logging...
if not exist "logs" mkdir "logs"
set "CLI_LOG=logs\cli_launch.log"
echo [%DATE% %TIME%] === OllamaOpt CLI Launch === >> "%CLI_LOG%"
echo [%DATE% %TIME%] Working directory: %CD% >> "%CLI_LOG%"

REM ================================================================
REM  Step 2 -- Python check
REM ================================================================
echo [Step 2/6] Checking Python...
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH. Install Python 3.8+ from https://python.org
    echo [%DATE% %TIME%] FATAL: python not found in PATH >> "%CLI_LOG%"
    pause
    exit /b 1
)
echo [%DATE% %TIME%] Python: OK >> "%CLI_LOG%"

REM ================================================================
REM  Step 3 -- venv activation
REM ================================================================
echo [Step 3/6] Activating virtual environment...
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    echo [%DATE% %TIME%] venv activated >> "%CLI_LOG%"
) else (
    echo [WARN] .venv not found -- using system Python
    echo [%DATE% %TIME%] WARN: .venv not found, using system Python >> "%CLI_LOG%"
)

REM ================================================================
REM  Step 4 -- Install / verify packages
REM ================================================================
echo [Step 4/6] Verifying packages...
python -m pip install -q rich requests psutil 2>nul
python -c "import rich, requests, psutil; from cli import ollama_cli" >nul 2>&1
if errorlevel 1 (
    echo [WARN] Package verification failed -- attempting verbose reinstall...
    echo [%DATE% %TIME%] WARN: package verify failed, attempting verbose reinstall >> "%CLI_LOG%"
    python -m pip install rich requests psutil
    echo.
    echo [ERROR] Could not import required modules after reinstall. See output above.
    echo [%DATE% %TIME%] FATAL: module imports still failing after reinstall >> "%CLI_LOG%"
    pause
    exit /b 1
)
echo [%DATE% %TIME%] Packages: OK (rich, requests, psutil, cli.ollama_cli) >> "%CLI_LOG%"

REM ================================================================
REM  Step 5 -- Backend detection
REM ================================================================
echo [Step 5/6] Detecting backend...
echo [%DATE% %TIME%] --- Backend detection start --- >> "%CLI_LOG%"

REM ----------------------------------------------------------------
REM  Tier 0 -- Is an Ollama server already running on port 11434?
REM  Use inline PowerShell for a clean HTTP probe -- no Python lag.
REM ----------------------------------------------------------------
powershell -NoProfile -NoLogo -ExecutionPolicy Bypass -Command ^
  "try { $null = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:11434/api/tags -TimeoutSec 2 -Proxy $null; exit 0 } catch { exit 1 }" ^
  >nul 2>&1
if not errorlevel 1 (
    set "BACKEND_MODE=existing"
    set "BACKEND_LABEL=Existing Server"
    echo [OK] Adopting existing Ollama server on port 11434
    echo [%DATE% %TIME%] Backend: EXISTING >> "%CLI_LOG%"
    goto backend_ready
)

REM ----------------------------------------------------------------
REM  Tier 1 -- Port is free; try to start the Intel GPU pipeline
REM ----------------------------------------------------------------
echo [INFO] No active server on port 11434. Trying Intel GPU pipeline...
echo [%DATE% %TIME%] Tier 1: attempting start_pipeline_simple.bat --server-only >> "%CLI_LOG%"

if exist "start_pipeline_simple.bat" (
    start "OllamaOpt Server" /min cmd /c "call start_pipeline_simple.bat --server-only"
    echo [INFO] Waiting for GPU pipeline - up to 30s...
    powershell -NoProfile -NoLogo -ExecutionPolicy Bypass -File "wait_for_api.ps1" -MaxRetries 30
    if not errorlevel 1 (
        set "BACKEND_MODE=gpu_pipeline"
        set "BACKEND_LABEL=Intel GPU Pipeline"
        echo [OK] Intel GPU pipeline is active
        echo [%DATE% %TIME%] Backend: GPU_PIPELINE >> "%CLI_LOG%"
        goto backend_ready
    )
    echo [WARN] GPU pipeline did not respond within 30s
    echo [%DATE% %TIME%] WARN: GPU pipeline timed out >> "%CLI_LOG%"
) else (
    echo [WARN] start_pipeline_simple.bat not found - skipping GPU tier
    echo [%DATE% %TIME%] WARN: start_pipeline_simple.bat missing >> "%CLI_LOG%"
)

REM ----------------------------------------------------------------
REM  Tier 2 -- GPU pipeline unavailable; fall back to plain ollama serve
REM  Print a very visible warning so the user knows GPU is not active.
REM ----------------------------------------------------------------
echo.
echo ################################################################
echo #  WARNING - FALLBACK MODE                                     #
echo #  Starting standard Ollama WITHOUT Intel GPU optimisation.    #
echo #  Token generation will be significantly slower.              #
echo #                                                              #
echo #  To restore GPU: run preflight_checks.bat                   #
echo #  Details: logs\cli_launch.log                               #
echo ################################################################
echo.
echo [%DATE% %TIME%] WARN: entering FALLBACK mode >> "%CLI_LOG%"

where ollama >nul 2>&1
if errorlevel 1 (
    echo [ERROR] ollama not found in PATH. Install from https://ollama.com
    echo [%DATE% %TIME%] FATAL: ollama not in PATH >> "%CLI_LOG%"
    pause
    exit /b 1
)

start "Ollama Fallback" /min cmd /c "ollama serve"
echo [INFO] Waiting for fallback Ollama - up to 20s...
powershell -NoProfile -NoLogo -ExecutionPolicy Bypass -File "wait_for_api.ps1" -MaxRetries 20
if errorlevel 1 (
    echo [ERROR] No Ollama server could be started. Run 'ollama serve' manually then retry.
    echo [%DATE% %TIME%] FATAL: fallback also failed >> "%CLI_LOG%"
    pause
    exit /b 1
)

set "BACKEND_MODE=fallback"
set "BACKEND_LABEL=Standard Ollama - fallback, no GPU"
echo [%DATE% %TIME%] Backend: FALLBACK >> "%CLI_LOG%"

REM ================================================================
REM  Step 6 -- Export env vars and launch Python CLI
REM ================================================================
:backend_ready
set "OLLAMAOPT_BACKEND_MODE=%BACKEND_MODE%"
set "OLLAMAOPT_BACKEND_LABEL=%BACKEND_LABEL%"
if "%BACKEND_MODE%"=="gpu_pipeline" (
    set "OLLAMAOPT_GPU_ACTIVE=1"
) else (
    set "OLLAMAOPT_GPU_ACTIVE=0"
)

echo.
echo [INFO] Backend : %BACKEND_LABEL%
echo [INFO] GPU opt : %OLLAMAOPT_GPU_ACTIVE%
echo [%DATE% %TIME%] Backend=%BACKEND_MODE% GPU=%OLLAMAOPT_GPU_ACTIVE% >> "%CLI_LOG%"
echo [Step 6/6] Launching OllamaOpt CLI...
echo.

python -m cli.ollama_cli %*

set "CLI_EXIT=%ERRORLEVEL%"
echo.
echo [INFO] CLI session ended
echo [%DATE% %TIME%] CLI exit code: %CLI_EXIT% >> "%CLI_LOG%"

if exist ".venv\Scripts\activate.bat" deactivate
pause
