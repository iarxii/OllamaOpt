@echo off
setlocal EnableDelayedExpansion
title Ollama Intel GPU + Logging Launcher

REM ================================
REM CHANGE TO PROJECT DIR
REM ================================
cd /d "%~dp0"

REM ================================
REM CONFIG
REM ================================
set "MODEL=qwen3.5:9b"
set "VENV_ACT=.venv\Scripts\activate.bat"
set "LOG_DIR=logs"

REM ================================
REM PREP LOGGING
REM ================================
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo Launch Time: %DATE% %TIME% > "%LOG_DIR%\env.txt"
echo MODEL=%MODEL% >> "%LOG_DIR%\env.txt"

REM ================================
REM TERMINAL 1: OLLAMA SERVER (LOGGED)
REM ================================
echo [INFO] Starting Ollama server...
start "Ollama Server (Intel GPU + Logs)" cmd /k ^
"(if exist %VENV_ACT% (call %VENV_ACT%) else (echo [WARN] Venv not found)) && ^
set OLLAMA_NUM_GPU=999 && ^
set ZES_ENABLE_SYSMAN=1 && ^
set SYCL_CACHE_PERSISTENT=1 && ^
set OLLAMA_DEBUG=1 && ^
set OLLAMA_LOG_LEVEL=debug && ^
set no_proxy=localhost,127.0.0.1 && ^
echo === ENVIRONMENT === >> logs\env.txt && ^
set >> logs\env.txt && ^
echo Starting Ollama server - logs: logs\ollama-server.log && ^
ollama serve 1>> logs\ollama-server.log 2>> logs\ollama-debug.log"

REM ================================
REM WAIT FOR SERVER
REM ================================
ping localhost -n 6 >nul

REM ================================
REM TERMINAL 2: BENCHMARK RUNNER
REM ================================
echo [INFO] Starting benchmark runner...
start "Ollama Benchmark" cmd /k ^
"(if exist %VENV_ACT% (call %VENV_ACT%) else (echo [WARN] Venv not found)) && ^
set no_proxy=localhost,127.0.0.1 && ^
echo Running ollamabench... && ^
call run_wait_for_api.bat && ^
python -m ollamabench.benchmark_runner %MODEL% --warmup-runs 2 > logs\benchmark-qwen39.txt && ^
echo Benchmark complete."

REM ================================
REM TERMINAL 3: CURL LATENCY PROBE
REM ================================
ping localhost -n 4 >nul

echo [INFO] Starting latency probe...
start "Ollama Latency Probe" cmd /k ^
"(if exist %VENV_ACT% (call %VENV_ACT%) else (echo [WARN] Venv not found)) && ^
set no_proxy=localhost,127.0.0.1 && ^
call run_latency_probe.bat -Model %MODEL% -OutputFile logs\curl-latency.log"

echo.
echo ================================================
echo Ollama launcher started!
echo ================================================
echo.
echo Logs available in: logs\
echo.

exit