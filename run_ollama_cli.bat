@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ================================================================
echo   OllamaOpt CLI  -  Local LLM Intel GPU Optimization
echo ================================================================
echo.

REM ================================================================
REM  Step 1 -- Logging setup
REM ================================================================
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
    echo [%DATE% %TIME%] venv activated: .venv\Scripts\activate.bat >> "%CLI_LOG%"
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
REM  If yes, adopt it as-is without touching anything.
REM ----------------------------------------------------------------
python -c "import requests; requests.get('http://localhost:11434/api/tags', timeout=2)" >nul 2>&1
if not errorlevel 1 (
    set "BACKEND_MODE=existing"
    set "BACKEND_LABEL=Existing Server"
    echo [OK] Using already-running Ollama server (no restart)
    echo [%DATE% %TIME%] Backend: EXISTING -- port 11434 already responding, no restart needed >> "%CLI_LOG%"
    goto backend_ready
)

REM ----------------------------------------------------------------
REM  Tier 1 -- Port is free; try to start the Intel GPU pipeline
REM ----------------------------------------------------------------
echo [INFO] No active server found on port 11434. Trying Intel GPU pipeline...
echo [%DATE% %TIME%] Port 11434 is free -- attempting Intel GPU pipeline >> "%CLI_LOG%"

if exist "start_ollama_server.bat" (
    echo [INFO] Launching start_ollama_server.bat in background (minimised^)...
    echo [%DATE% %TIME%] Launching start_ollama_server.bat /min >> "%CLI_LOG%"
    start "OllamaOpt GPU Server" /min cmd /c "call start_ollama_server.bat"
    echo [INFO] Waiting for GPU pipeline to respond (up to 30s^)...
    call run_wait_for_api.bat -MaxRetries 30
    if not errorlevel 1 (
        set "BACKEND_MODE=gpu_pipeline"
        set "BACKEND_LABEL=Intel GPU Pipeline"
        echo [OK] Intel GPU pipeline is active
        echo [%DATE% %TIME%] Backend: GPU_PIPELINE -- Intel GPU pipeline started and responding >> "%CLI_LOG%"
        goto backend_ready
    )
    echo [WARN] GPU pipeline did not respond within 30 seconds
    echo [%DATE% %TIME%] WARN: GPU pipeline timed out after 30s, falling through to Tier 2 >> "%CLI_LOG%"
) else (
    echo [WARN] start_ollama_server.bat not found -- skipping GPU pipeline tier
    echo [%DATE% %TIME%] WARN: start_ollama_server.bat not found, GPU pipeline tier skipped >> "%CLI_LOG%"
)

REM ----------------------------------------------------------------
REM  Tier 2 -- GPU pipeline unavailable; fall back to plain ollama serve
REM  Print a very visible warning so the user knows GPU is not active.
REM ----------------------------------------------------------------
echo.
echo ################################################################
echo #                                                              #
echo #   WARNING  --  FALLBACK MODE ACTIVE                         #
echo #                                                              #
echo #   Starting standard Ollama WITHOUT Intel GPU optimisation.   #
echo #   Token generation will be SIGNIFICANTLY SLOWER than the    #
echo #   GPU-accelerated pipeline.                                  #
echo #                                                              #
echo #   To restore GPU acceleration:                               #
echo #     - Run  preflight_checks.bat   to diagnose the env       #
echo #     - Run  start_ollama_server.bat  to start the pipeline   #
echo #                                                              #
echo #   Full details logged to:  logs\cli_launch.log              #
echo #                                                              #
echo ################################################################
echo.
echo [%DATE% %TIME%] WARN: entering FALLBACK mode (plain ollama serve, no GPU optimisation) >> "%CLI_LOG%"

where ollama >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 'ollama' not found in PATH. Install from https://ollama.com then retry.
    echo [%DATE% %TIME%] FATAL: 'ollama' binary not found in PATH -- fallback impossible >> "%CLI_LOG%"
    pause
    exit /b 1
)

echo [INFO] Starting standard ollama serve in background (minimised^)...
echo [%DATE% %TIME%] Launching 'ollama serve' /min >> "%CLI_LOG%"
start "Ollama Fallback" /min cmd /c "ollama serve"
echo [INFO] Waiting for fallback Ollama to respond (up to 20s^)...
call run_wait_for_api.bat -MaxRetries 20
if errorlevel 1 (
    echo.
    echo [ERROR] No Ollama server could be started.
    echo [ERROR] Run 'ollama serve' manually in a separate window, then retry.
    echo [%DATE% %TIME%] FATAL: fallback 'ollama serve' also failed to respond within 20s >> "%CLI_LOG%"
    echo [%DATE% %TIME%] FATAL: no backend available, aborting launch >> "%CLI_LOG%"
    pause
    exit /b 1
)

set "BACKEND_MODE=fallback"
set "BACKEND_LABEL=Standard Ollama (fallback - no GPU)"
echo [%DATE% %TIME%] Backend: FALLBACK -- standard ollama serve running, no GPU optimisation >> "%CLI_LOG%"

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

echo [INFO] Backend mode : %BACKEND_LABEL%
echo [INFO] GPU active   : %OLLAMAOPT_GPU_ACTIVE%
echo [Step 6/6] Launching OllamaOpt CLI...
echo.
echo [%DATE% %TIME%] OLLAMAOPT_BACKEND_MODE=%BACKEND_MODE% >> "%CLI_LOG%"
echo [%DATE% %TIME%] OLLAMAOPT_BACKEND_LABEL=%BACKEND_LABEL% >> "%CLI_LOG%"
echo [%DATE% %TIME%] OLLAMAOPT_GPU_ACTIVE=%OLLAMAOPT_GPU_ACTIVE% >> "%CLI_LOG%"
echo [%DATE% %TIME%] Launching: python -m cli.ollama_cli >> "%CLI_LOG%"

python -m cli.ollama_cli %*

set "CLI_EXIT=%ERRORLEVEL%"
echo.
echo [INFO] CLI session ended
echo [%DATE% %TIME%] CLI session ended (exit code: %CLI_EXIT%) >> "%CLI_LOG%"
echo [%DATE% %TIME%] ================================================== >> "%CLI_LOG%"

if exist ".venv\Scripts\activate.bat" deactivate
pause
