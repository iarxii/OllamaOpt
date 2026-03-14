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
echo [INFO] Starting Ollama server with Intel GPU optimization...
start "Ollama Server (Intel GPU + Logs)" cmd /k "call start_ollama_server.bat"

REM ================================
REM WAIT FOR SERVER
REM ================================
echo [INFO] Waiting for Ollama server to initialize (15 seconds)...
ping localhost -n 16 >nul

REM ================================
REM TERMINAL 2: BENCHMARK RUNNER
REM ================================
echo [INFO] Starting benchmark runner...
rem If you want to *see* the upload prompt and answer it interactively,
rem set environment variable SHOW_BENCH_PROMPT=1 before running this script.

if "%SHOW_BENCH_PROMPT%"=="1" goto :bench_interactive
goto :bench_auto

:bench_interactive
rem Run the benchmark inline so the interactive upload prompt appears in this console
echo Running interactive benchmark in the current console...
if exist %VENV_ACT% call %VENV_ACT%
set no_proxy=localhost,127.0.0.1
echo Running ollamabench...
call run_wait_for_api.bat
python -m ollamabench.benchmark_runner %MODEL% --warmup-runs 2
echo Benchmark complete.
goto :after_bench

:bench_auto
start "Ollama Benchmark" cmd /k "(if exist %VENV_ACT% call %VENV_ACT%) & set no_proxy=localhost,127.0.0.1 & echo Running ollamabench... & call run_wait_for_api.bat & echo n ^| python -m ollamabench.benchmark_runner %MODEL% --warmup-runs 2 > logs\benchmark-qwen39.txt & echo Benchmark complete."

:after_bench

REM ================================
REM TERMINAL 3: CURL LATENCY PROBE
REM ================================
ping localhost -n 4 >nul

echo [INFO] Starting latency probe...
start "Ollama Latency Probe" cmd /k ^
"(if exist %VENV_ACT% call %VENV_ACT%) & ^
set no_proxy=localhost,127.0.0.1 & ^
call run_latency_probe.bat -Model %MODEL% -OutputFile logs\curl-latency.log"

echo.
echo ================================================
echo Ollama launcher started!
echo ================================================
echo.
echo Logs available in: logs\
echo.

exit