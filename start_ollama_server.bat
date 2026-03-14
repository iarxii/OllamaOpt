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
set "OLLAMA_LOG_LEVEL=debug"
set "no_proxy=localhost,127.0.0.1"

REM =====================================================
REM Activate venv if exists
REM =====================================================
if exist ".venv\Scripts\activate.bat" (
  call .venv\Scripts\activate.bat
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
echo OLLAMA_LOG_LEVEL=%OLLAMA_LOG_LEVEL%
echo.
echo Waiting 3 seconds before startup to ensure port is free...
ping localhost -n 4 >nul
echo Starting Ollama serve...
echo.

REM =====================================================
REM Start Ollama with full GPU offload
REM =====================================================
ollama serve 1>> logs\ollama-server.log 2>> logs\ollama-debug.log
