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
REM 1) Graceful shutdown via CLI (best effort)
REM =====================================================
echo [INFO] Attempting graceful Ollama shutdown...
ollama stop all >nul 2>&1
ping localhost -n 2 >nul

REM =====================================================
REM 2) Force kill all Ollama and related processes
REM =====================================================
echo [INFO] Force-terminating all Ollama processes...
taskkill /f /im ollama.exe /t >nul 2>&1
taskkill /f /im "ollama app.exe" /t >nul 2>&1
echo [OK]  Ollama processes terminated.
ping localhost -n 2 >nul

REM =====================================================
REM 3) Force kill launcher terminals and python
REM =====================================================
echo [INFO] Terminating launcher terminals...
taskkill /f /im cmd.exe /fi "WINDOWTITLE eq Ollama Server (Intel GPU + Logs)" >nul 2>&1
taskkill /f /im cmd.exe /fi "WINDOWTITLE eq Ollama Benchmark" >nul 2>&1
taskkill /f /im cmd.exe /fi "WINDOWTITLE eq Ollama Latency Probe" >nul 2>&1
taskkill /f /im cmd.exe /fi "WINDOWTITLE eq Ollama Intel GPU + Logging Launcher" >nul 2>&1
taskkill /f /im python.exe /t >nul 2>&1
echo [OK]  Launcher terminals terminated
ping localhost -n 2 >nul

REM =====================================================
REM 4) Wait for port to be released
REM =====================================================
echo [INFO] Waiting for port 11434 to be released...
for /l %%i in (1,1,10) do (
  netstat -ano | find ":11434" >nul
  if errorlevel 1 (
    echo [OK]  Port 11434 is now free.
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
echo  Kill process complete.
echo ================================================
echo.

endlocal
pause
