@echo off
REM Configure Intel GPU environment variables and start Ollama server
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

REM =====================================================
REM Intel GPU Configuration
REM =====================================================
set "OLLAMA_NUM_GPU=999"
set "ZES_ENABLE_SYSMAN=1"
set "SYCL_CACHE_PERSISTENT=1"
set "OLLAMA_DEBUG=1"
set "OLLAMA_INTEL_GPU=true"
set "OLLAMA_LOG_LEVEL=debug"
set "no_proxy=localhost,127.0.0.1"

REM =====================================================
REM Activate venv if exists
REM =====================================================
if exist ".venv\Scripts\activate.bat" (
  call .venv\Scripts\activate.bat
)

REM =====================================================
REM Pre-flight check for Ollama executable
REM =====================================================
where ollama >nul 2>&1
if errorlevel 1 (
  echo.
  echo [FATAL ERROR] 'ollama.exe' not found in your system's PATH.
  echo Please ensure Ollama is installed correctly and your PATH is configured.
  echo You can download Ollama from: https://ollama.com
  echo.
  pause
  exit /b 1
)

REM =====================================================
REM Log environment
REM =====================================================
echo === OLLAMA SERVER START ===
echo Timestamp: %DATE% %TIME%
echo OLLAMA_NUM_GPU=%OLLAMA_NUM_GPU%
echo ZES_ENABLE_SYSMAN=%ZES_ENABLE_SYSMAN%
echo SYCL_CACHE_PERSISTENT=%SYCL_CACHE_PERSISTENT%
echo OLLAMA_DEBUG=%OLLAMA_DEBUG%
echo OLLAMA_INTEL_GPU=%OLLAMA_INTEL_GPU%
echo OLLAMA_LOG_LEVEL=%OLLAMA_LOG_LEVEL%
echo.
echo Waiting 3 seconds before startup to ensure port is free...
ping localhost -n 4 >nul
echo Starting Ollama serve...
echo If this window returns to a command prompt, the server has failed to start.
echo Check logs for details:
echo   - logs\ollama-server.log
echo   - logs\ollama-debug.log
echo.
echo ============================= WATCH THIS WINDOW =============================
echo If an error appears below (e.g., 'bind', 'driver error'), that is the root cause.
echo The server is running correctly if you see messages like 'Listening on...'
echo If this window closes or returns to a prompt, the server has FAILED.
echo ===========================================================================
echo.

REM =====================================================
REM Start Ollama with full GPU offload
REM If OLLAMA_DEBUG_INTERACTIVE is set to 1, run directly in the console.
REM Otherwise, redirect to a log file for unattended runs.
REM =====================================================
if "%OLLAMA_DEBUG_INTERACTIVE%"=="1" (
  echo [INFO] Running in INTERACTIVE debug mode. Output will appear below.
  ollama serve
) else (
  if not exist "logs" mkdir "logs"
  ollama serve > "logs\ollama_server.log" 2>&1
)

REM =====================================================
REM ERROR HANDLING (only reached if 'ollama serve' fails on startup)
REM =====================================================
if errorlevel 1 (
  echo.
  echo =================================================================
  echo [FATAL ERROR] Ollama server failed to start or has crashed!
  echo =================================================================
  echo.
  echo This can happen for several reasons:
  echo   1. Another Ollama instance is already running (check port 11434).
  echo   2. A critical error occurred (e.g., driver issue, corrupted model).
  echo.
  echo Please check the following log files for detailed error messages:
  echo   - "logs\ollama-server.log"
  echo   - "logs\ollama-debug.log"
  echo.
  echo You can use 'kill_ollama.bat' to stop any lingering processes
  echo and then try running 'start_clean.bat' for a fresh start.
  echo.
)

pause
