@echo off
setlocal enabledelayedexpansion
title OllamaOpt - Pre-flight Checks
cd /d "%~dp0"

echo.
echo ================================================
echo  OllamaOpt - Pre-flight Checks
echo ================================================
echo.

set FAIL_COUNT=0

REM Check 1: Python
echo [CHECK 1/4] Python installation...
where python >nul 2>&1
if errorlevel 1 (
  echo [FAIL] Python not found
  set /a FAIL_COUNT=FAIL_COUNT+1
) else (
  echo [OK]   Python is installed
)
echo.

REM Check 2: Ollama
echo [CHECK 2/4] Ollama installation...
where ollama >nul 2>&1
if errorlevel 1 (
  echo [FAIL] Ollama not found
  set /a FAIL_COUNT=FAIL_COUNT+1
) else (
  echo [OK]   Ollama is installed
)
echo.

REM Check 3: Port 11434 - kill Ollama if in use
echo [CHECK 3/4] Port 11434 availability...
netstat -ano > "%temp%\netstat.txt" 2>nul
findstr ":11434" "%temp%\netstat.txt" >nul 2>&1
if errorlevel 1 (
  REM Port is free
  echo [OK]   Port 11434 is available
) else (
  REM Port is in use - kill Ollama
  echo [WARN] Port 11434 in use - terminating Ollama...
  taskkill /f /im ollama.exe >nul 2>&1
  taskkill /f /im "ollama app.exe" >nul 2>&1
  
  REM Wait for port to release (up to 10 seconds)
  set PORT_FREED=0
  echo        Waiting for port to release...
  for /l %%i in (1,1,10) do (
    if !PORT_FREED! EQU 0 (
      timeout /t 1 >nul
      netstat -ano > "%temp%\netstat.txt" 2>nul
      findstr ":11434" "%temp%\netstat.txt" >nul 2>&1
      if errorlevel 1 (
        echo [OK]   Port 11434 is now available
        set PORT_FREED=1
      )
    )
  )
  if !PORT_FREED! EQU 0 (
    echo [FAIL] Port 11434 still in use after timeout
    set /a FAIL_COUNT=FAIL_COUNT+1
  )
)
if exist "%temp%\netstat.txt" del "%temp%\netstat.txt"
echo.

REM Check 4: Intel GPU
echo [CHECK 4/4] Intel GPU detection...
powershell -NoProfile -NoLogo -Command "if (Get-WmiObject Win32_VideoController | Where-Object {$_.Name -like '*Intel*'}) { exit 0 } else { exit 1 }" >nul 2>&1
set GPU_CHECK=!errorlevel!
if %GPU_CHECK% EQU 0 (
  echo [OK]   Intel GPU detected
) else (
  echo [WARN] Intel GPU not detected
)

echo.
echo ================================================
echo.

if %FAIL_COUNT% EQU 0 (
  echo All checks passed - launching start_dev.bat...
  echo.
  call start_dev.bat
) else (
  echo Checks failed: %FAIL_COUNT% issue(s) found
  pause
)

endlocal



