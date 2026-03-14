@echo off
setlocal EnableExtensions EnableDelayedExpansion
title OllamaOpt - Pre-flight Checks

cd /d "%~dp0"

echo.
echo ================================================
echo  OllamaOpt - Pre-flight Checks
echo ================================================
echo.

set /a FAIL_COUNT=0

REM =====================================================
REM 1) Check Python
REM =====================================================
echo [CHECK 1/4] Python installation...
where python >nul 2>&1
if errorlevel 1 (
  echo [FAIL] Python not found in PATH
  echo        Install Python 3.10+ and ensure 'python' is available
  set /a FAIL_COUNT+=1
) else (
  python --version | findstr /r "3\.[0-9]" >nul
  if errorlevel 1 (
    echo [FAIL] Python version is not Python 3.x
    set /a FAIL_COUNT+=1
  ) else (
    echo [OK]   Python is installed
  )
)

echo.

REM =====================================================
REM 2) Check Ollama
REM =====================================================
echo [CHECK 2/4] Ollama installation...
where ollama >nul 2>&1
if errorlevel 1 (
  echo [FAIL] Ollama not found in PATH
  echo        Install Ollama from https://ollama.ai and add to PATH
  set /a FAIL_COUNT+=1
) else (
  echo [OK]   Ollama is installed
)

echo.

REM =====================================================
REM 3) Check Port 11434
REM =====================================================
echo [CHECK 3/4] Port 11434 availability...
netstat -ano | findstr ":11434" >nul 2>&1
if not errorlevel 1 (
  echo [FAIL] Port 11434 is already in use!
  echo.
  echo        This port is likely being used by:
  echo        - Ollama GUI/background service
  echo        - Previous Ollama process
  echo.
  echo        To fix:
  echo        1) Close the Ollama app (check Task Manager)
  echo        2) Run: taskkill /f /im ollama.exe
  echo        3) Run: sc stop ollama (if installed as service)
  echo        4) Then run this script again
  echo.
  set /a FAIL_COUNT+=1
) else (
  echo [OK]   Port 11434 is available
)

echo.

REM =====================================================
REM 4) Check Intel GPU
REM =====================================================
echo [CHECK 4/4] Intel GPU detection...
powershell -NoProfile -NoLogo -Command "Get-WmiObject -Class Win32_VideoController | Where-Object { $_.Name -match 'Intel' }" >nul 2>&1
if errorlevel 1 (
  echo [WARN] No Intel GPU detected
  echo        The system may not have Intel Arc/Xe GPU
  echo        Ollama will fall back to CPU (much slower)
) else (
  echo [OK]   Intel GPU detected
)

echo.
echo ================================================

if %FAIL_COUNT% EQU 0 (
  echo  All checks passed! Ready to launch.
  echo ================================================
  echo.
  echo Starting dev environment in 3 seconds...
  ping localhost -n 4 >nul
  start_dev.bat
) else (
  echo  !FAIL_COUNT! check(s) failed. Please resolve above.
  echo ================================================
  echo.
  pause
)

endlocal
