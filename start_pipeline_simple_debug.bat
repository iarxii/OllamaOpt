@echo on
setlocal EnableDelayedExpansion
title OllamaOpt - Single Pipeline Runner (DEBUG)

cd /d "%~dp0"

echo =====================================================
echo OllamaOpt - Single Pipeline Runner (DEBUG)
echo =====================================================

set LOG_DIR=logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo Launch Time: %DATE% %TIME% > "%LOG_DIR%\env.txt"

echo [STEP 1] Kill existing Ollama/python processes (best-effort)
taskkill /f /im ollama.exe /t >nul 2>&1
taskkill /f /im "ollama app.exe" /t >nul 2>&1
taskkill /f /im python.exe /t >nul 2>&1

echo [STEP 2] Ensure port 11434 is free
set /a _port_try=1
:port_loop
    echo DEBUG: loop iteration %_port_try%
    netstat -ano | findstr ":11434" >nul
    echo DEBUG: findstr exitlevel=%errorlevel%
    if errorlevel 1 (
        echo [OK] Port 11434 is free
        goto port_ready
    )
    if %_port_try% GEQ 10 goto port_warn
    echo Waiting for port to free (attempt %_port_try%)...
    set /a _port_try+=1
    ping localhost -n 2 >nul
    goto port_loop
:port_warn
echo [WARN] Port 11434 may be in use; continuing anyway
:port_ready

echo [STEP 3] Start Ollama server with GPU env and redirect logs
set "OLLAMA_NUM_GPU=999"
set "ZES_ENABLE_SYSMAN=1"
set "SYCL_CACHE_PERSISTENT=1"
set "OLLAMA_DEBUG=1"
set "OLLAMA_LOG_LEVEL=debug"

start "OllamaServer_bg" /b cmd /c "ollama serve 1> "%LOG_DIR%\ollama-server.log" 2> "%LOG_DIR%\ollama-debug.log""
echo [INFO] Waiting 8 seconds for server to initialize...
ping localhost -n 9 >nul

echo [STEP 4] Wait for API health
powershell -NoProfile -Command "for ($i=0;$i -lt 30;$i++) { try { Invoke-WebRequest -UseBasicParsing http://localhost:11434/api/version -TimeoutSec 5; Write-Host 'API OK'; exit 0 } catch { Start-Sleep -Seconds 1 } } exit 1" > "%LOG_DIR%\wait_for_api.txt" 2>&1
if errorlevel 1 (
    echo [ERROR] Ollama API did not respond; see %LOG_DIR%\wait_for_api.txt
    exit /b 1
)

echo [STEP 5] Run benchmark (auto-skip upload) and capture output
set MODEL=qwen3.5:9b
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set no_proxy=localhost,127.0.0.1
echo n | python -m ollamabench.benchmark_runner %MODEL% --warmup-runs 2 > "%LOG_DIR%\benchmark-qwen39.txt" 2>&1
if errorlevel 1 (
    echo [ERROR] Benchmark failed; check %LOG_DIR%\benchmark-qwen39.txt
)

echo [STEP 6] Send validation prompt to API and save response
set "_pyfile=%TEMP%\ollama_test_prompt.py"
> "%_pyfile%" echo import json,urllib.request,sys
>> "%_pyfile%" echo payload=json.dumps({"model":"%MODEL%","prompt":"Return OK only.","stream":False}).encode()
>> "%_pyfile%" echo req=urllib.request.Request('http://localhost:11434/api/generate', data=payload, headers={'Content-Type':'application/json'})
>> "%_pyfile%" echo try:
>> "%_pyfile%" echo     resp=urllib.request.urlopen(req, timeout=300)
>> "%_pyfile%" echo     print(resp.read().decode())
>> "%_pyfile%" echo except Exception as e:
>> "%_pyfile%" echo     print('PROMPT_ERROR:', e)
>> "%_pyfile%" echo     sys.exit(1)
python "%_pyfile%" > "%LOG_DIR%\test_prompt_response.json" 2>&1
set "_pyret=%ERRORLEVEL%"
del "%_pyfile%" >nul 2>&1
if %_pyret% NEQ 0 (
    echo [ERROR] Validation prompt failed; see %LOG_DIR%\test_prompt_response.json
)

echo [STEP 7] Run latency probe
call run_latency_probe.bat -Model %MODEL% -OutputFile "%LOG_DIR%\curl-latency.log"

echo =====================================================
echo Pipeline complete. Logs in %LOG_DIR%\
echo =====================================================
endlocal
