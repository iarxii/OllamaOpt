@echo off
setlocal EnableExtensions EnableDelayedExpansion
title OllamaOpt - Kill Ollama Processes

REM =====================================================
REM Kill Ollama Processes
REM =====================================================
echo.
echo ================================================
echo  OllamaOpt - Kill Ollama Processes
echo ================================================
echo.

REM =====================================================
REM 1) Graceful shutdown via CLI
REM =====================================================
echo [INFO] Attempting graceful Ollama shutdown...
ollama stop all >nul 2>&1

REM =====================================================
REM 2) Wait for graceful shutdown
REM =====================================================
ping localhost -n 3 >nul

REM =====================================================
REM 3) Check if ollama.exe is still running
REM =====================================================
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /i "ollama" >nul
if errorlevel 1 (
  echo [OK]  Ollama gracefully stopped
  goto :done
)

REM =====================================================
REM 4) Force kill ollama.exe if still running
REM =====================================================
echo [WARN] Ollama still running - forcing termination
taskkill /f /im ollama.exe >nul 2>&1
if errorlevel 0 (
  echo [OK]  Ollama process forcefully terminated
) else (
  echo [WARN] Could not taskkill ollama.exe (may already be stopped)
)

REM =====================================================
REM 5) Wait for port to be released
REM =====================================================
echo [INFO] Waiting for port 11434 to be released...
for /l %%i in (1,1,10) do (
  netstat -ano | find ":11434" >nul
  if errorlevel 1 (
    echo [OK]  Port 11434 is now free
    goto :done
  )
  ping localhost -n 2 >nul
)
echo [WARN] Port 11434 may still be in use

REM =====================================================
REM Done
REM =====================================================
:done
echo.
echo ================================================
echo  Ollama processes killed
echo ================================================
echo.

endlocal
pause
