@echo off
setlocal EnableDelayedExpansion
title Ollama Intel GPU + Logging Launcher

REM ================================
REM CONFIG
REM ================================
set "MODEL=qwen3.5:8B"
set "ROOT=%~dp0"
set "LOG_DIR=%ROOT%logs"
set "VENV_ACT=%ROOT%.venv\Scripts\activate.bat"

REM ================================
REM PREP LOGGING
REM ================================
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo Launch Time: %DATE% %TIME% > "%LOG_DIR%\env.txt"
echo MODEL=%MODEL% >> "%LOG_DIR%\env.txt"
echo ROOT=%ROOT% >> "%LOG_DIR%\env.txt"

REM ================================
REM TERMINAL 1: OLLAMA SERVER (LOGGED)
REM ================================
start "Ollama Server (Intel GPU + Logs)" cmd /k ^
"
REM --- Activate local venv (project venv)
if exist \"%VENV_ACT%\" (call \"%VENV_ACT%\") else (echo [WARN] Venv not found: %VENV_ACT%)

REM ---- Intel GPU offload (CRITICAL)
set OLLAMA_NUM_GPU=999
set ZES_ENABLE_SYSMAN=1
set SYCL_CACHE_PERSISTENT=1

REM ---- Logging
set OLLAMA_DEBUG=1
set OLLAMA_LOG_LEVEL=debug
set no_proxy=localhost,127.0.0.1

echo === ENVIRONMENT === >> \"%LOG_DIR%\env.txt\"
set >> \"%LOG_DIR%\env.txt\"

echo Starting Ollama server...
echo Logs: %LOG_DIR%\ollama-server.log

ollama serve ^
  1>> \"%LOG_DIR%\ollama-server.log\" ^
  2>> \"%LOG_DIR%\ollama-debug.log\"
"

REM ================================
REM WAIT FOR SERVER
REM ================================
timeout /t 5 >nul

REM ================================
REM TERMINAL 2: BENCHMARK RUNNER
REM ================================
start "Ollama Benchmark" cmd /k ^
"
if exist \"%VENV_ACT%\" (call \"%VENV_ACT%\") else (echo [WARN] Venv not found: %VENV_ACT%)
set no_proxy=localhost,127.0.0.1

echo Waiting for Ollama API to respond...
powershell -Command ^
\"for ($i=0; $i -lt 10; $i++) { ^
  try { ^
    $r = Invoke-WebRequest -UseBasicParsing http://localhost:11434/api/tags -TimeoutSec 2; ^
    if ($r.StatusCode -eq 200) { Write-Host 'Ollama is up.'; exit 0 } ^
  } catch {} ^
  Start-Sleep -Seconds 1 ^
} ^
Write-Host 'Ollama did not respond in time.'; exit 1\" ^
|| (echo [FAIL] Ollama server not responding. Check Terminal 1 logs. & exit /b)

echo Running ollamabench...
echo Output: %LOG_DIR%\benchmark-qwen35.txt

python -m ollamabench.benchmark_runner %MODEL% --warmup-runs 2 ^
  > \"%LOG_DIR%\benchmark-qwen35.txt\"

echo Benchmark complete.
"

REM ================================
REM TERMINAL 3: CURL LATENCY PROBE
REM ================================
start "Ollama Latency Probe" cmd /k ^
"
if exist \"%VENV_ACT%\" (call \"%VENV_ACT%\") else (echo [WARN] Venv not found: %VENV_ACT%)
set no_proxy=localhost,127.0.0.1

echo Running curl latency test...
echo Output: %LOG_DIR%\curl-latency.log

powershell -Command ^
\"Measure-Command { ^
  curl http://localhost:11434/api/generate `
    -H 'Content-Type: application/json' `
    -d '{ \\\"model\\\": \\\"%MODEL%\\\", \\\"prompt\\\": \\\"Return OK only.\\\", \\\"stream\\\": false }' ^
} | Out-File -Append '%LOG_DIR%\\curl-latency.log'\"

echo Done.
"

exit