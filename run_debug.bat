@echo off
setlocal enabledelayedexpansion
echo on

REM ======================================================
REM OllamaOpt - Clean Execution Script (Debug)
REM Adds echo on to trace commands
REM ======================================================

title OllamaOpt Clean Start (Debug)

cd /d "%~dp0"

echo.
echo ======================================================
echo OllamaOpt Clean Start (Debug)
echo ======================================================
echo.
echo This script will:
echo  1. Kill all Ollama and Python processes
echo  2. Wait for port 11434 to be released
echo  3. Start Ollama with GPU optimization
echo  4. Run diagnostics
echo.

REM Step 1: Kill all related processes
echo [STEP 1] Terminating old processes...
taskkill /f /im ollama.exe /t >nul 2>&1
taskkill /f /im "ollama app.exe" /t >nul 2>&1
taskkill /f /im python.exe /t >nul 2>&1
echo [OK] Processes terminated

REM Step 2: Wait for port release
echo [STEP 2] Waiting for port 11434 to be released...
for /l %%i in (1,1,30) do (
  netstat -ano > "%temp%\port_check.txt" 2>nul
  findstr ":11434" "%temp%\port_check.txt" >nul 2>&1
  if errorlevel 1 (
    echo [OK] Port is now available
    goto port_ready
  )
  ping localhost -n 2 >nul
)
echo [WARN] Port may still be occupied, trying anyway...

:port_ready
if exist "%temp%\port_check.txt" del "%temp%\port_check.txt"

REM Step 3: Launch pipeline
echo.
echo [STEP 3] Launching OllamaOpt pipeline...
echo.
call start_dev.bat

REM Add a delay to allow the server to start
echo.
echo [INFO] Waiting 5 seconds for the server to initialize...
ping localhost -n 6 >nul

REM Step 4: Run diagnostics
echo.
echo [STEP 4] Running GPU diagnostics...
echo.
powershell.exe -ExecutionPolicy Bypass -File "gpu_diagnostics.ps1"


:end
endlocal
