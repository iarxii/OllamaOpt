@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

title OllamaOpt - Smart Pipeline Runner

echo.
echo ======================================================
echo   OllamaOpt - Smart Pipeline Runner
echo ======================================================
echo.
echo This script will:
echo   1. Start the full Ollama application pipeline.
echo   2. Wait for the server to initialize.
echo   3. Run GPU diagnostics to verify offload is working.
echo   4. Report success or failure.
echo.

REM ======================================================
REM 1. Start the application using the existing dev script
REM This will open new terminals for the server, benchmark, etc.
REM ======================================================
echo [INFO] Starting the Ollama development environment...
start "OllamaOpt Dev Env" cmd /c "call start_dev.bat"

REM ======================================================
REM 2. Wait for the Ollama API to be responsive
REM ======================================================
echo [INFO] Waiting for the Ollama server to come online...
REM Give it a few seconds to start the new terminals
ping localhost -n 10 >nul
call run_wait_for_api.bat
if !errorlevel! neq 0 (
    echo.
    echo [FATAL ERROR] The Ollama server did not become available.
    echo Please check the "Ollama Server" window for startup errors.
    echo.
    pause
    exit /b 1
)
echo [OK] Ollama server is online.
echo.

REM ======================================================
REM 3. Run GPU Diagnostics
REM ======================================================
echo [INFO] Running GPU diagnostics to verify offload status...
if not exist "logs" mkdir "logs"
powershell -NoProfile -NoLogo -ExecutionPolicy Bypass -File "gpu_diagnostics.ps1" > "logs\gpu_diagnostics.log" 2>&1

REM ======================================================
REM 4. Check Diagnostics Result and Report
REM ======================================================
echo [INFO] Analyzing diagnostics results...

findstr /C:"[PASS] GPU offload is ACTIVE!" "logs\gpu_diagnostics.log" >nul
if !errorlevel! equ 0 (
    echo.
    echo =================================================================
    echo  [SUCCESS] GPU Offload is ACTIVE and Verified!
    echo =================================================================
    echo.
    echo The application is now running. Check the other terminals for:
    echo   - "Ollama Server"
    echo   - "Ollama Benchmark"
    echo   - "Ollama Latency Probe"
    echo.
) else (
    echo.
    echo [FATAL ERROR] GPU offload is NOT working or could not be verified.
    echo =================================================================
    echo Please check the log file for details:
    echo   c:\AppDev\OllamaOpt - Local LLM Intel GPU Optimization\logs\gpu_diagnostics.log
    echo.
    echo The most likely cause is an Intel GPU driver issue.
    echo See the "Next Steps" in the log for recommendations.
    echo.
    echo [ACTION] Terminating the server to prevent running in a broken state.
    echo =================================================================
    echo.
    call kill_ollama.bat
)

pause
endlocal
