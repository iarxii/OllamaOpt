@echo off
setlocal enabledelayedexpansion

REM ======================================================
REM OllamaOpt - Clean Execution Script
REM Handles port conflicts and starts fresh
REM ======================================================

title OllamaOpt Clean Start

cd /d "%~dp0"

echo.
echo ======================================================
echo OllamaOpt Clean Start
echo ======================================================
echo.
echo This script will:
echo  1. Kill all Ollama and Python processes
echo  2. Wait for port 11434 to be released
echo  3. Start Ollama with GPU optimization
echo  4. Run benchmarks
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
call preflight_checks.bat

:end
endlocal
