@echo off
setlocal EnableExtensions EnableDelayedExpansion
title OllamaOpt - Clean Reset

REM =====================================================
REM CONFIG
REM =====================================================
set "ROOT=%~dp0"
set "LOG_DIR=%ROOT%logs"
set "ARCHIVE_ROOT=%ROOT%logs_archive"
set "OLLAMA_PORT=11434"

REM =====================================================
REM TIMESTAMP
REM =====================================================
for /f "tokens=1-4 delims=/ " %%a in ("%DATE%") do (
  set YYYY=%%d
  set MM=%%b
  set DD=%%c
)
for /f "tokens=1-3 delims=:." %%a in ("%TIME%") do (
  set HH=%%a
  set MI=%%b
  set SS=%%c
)
set TS=%YYYY%%MM%%DD%_%HH%%MI%%SS%

echo.
echo ================================================
echo  OllamaOpt - Clean Reset
echo  %TS%
echo ================================================
echo.

REM =====================================================
REM 1) Stop Ollama (graceful)
REM =====================================================
echo [INFO] Attempting graceful Ollama shutdown...
ollama stop all >nul 2>&1

REM =====================================================
REM 2) Kill Ollama process if still running
REM =====================================================
echo [INFO] Forcing termination of all Ollama processes...
taskkill /f /im ollama.exe /t >nul 2>&1
taskkill /f /im "ollama app.exe" /t >nul 2>&1
ping localhost -n 2 >nul
echo [OK] Ollama processes terminated.

REM =====================================================
REM 3) Wait for port to be free
REM =====================================================
echo [INFO] Waiting for port %OLLAMA_PORT% to be released...
for /l %%i in (1,1,10) do (
  netstat -ano | find ":%OLLAMA_PORT%" >nul 2>&1
  if errorlevel 1 (
    echo [OK]  Port %OLLAMA_PORT% is now free
    goto :port_free
  )
  ping localhost -n 2 >nul
)
echo [WARN] Port %OLLAMA_PORT% may still be in use

:port_free

REM =====================================================
REM 4) Archive logs (if any)
REM =====================================================
if exist "%LOG_DIR%" (
  if not exist "%ARCHIVE_ROOT%" mkdir "%ARCHIVE_ROOT%"
  set "ARCHIVE_DIR=%ARCHIVE_ROOT%\logs_%TS%"
  echo [INFO] Archiving logs to:
  echo        %ARCHIVE_DIR%
  mkdir "%ARCHIVE_DIR%"
  xcopy "%LOG_DIR%\*" "%ARCHIVE_DIR%\" /E /I /Y >nul
) else (
  echo [INFO] No logs directory found to archive
)

REM =====================================================
REM 5) Clear active logs directory
REM =====================================================
if exist "%LOG_DIR%" (
  echo [INFO] Clearing logs directory...
  rmdir /s /q "%LOG_DIR%"
)
mkdir "%LOG_DIR%"

REM =====================================================
REM 6) OPTIONAL: Clear Ollama model cache (DISABLED)
REM =====================================================
REM WARNING: Uncomment ONLY if you want to remove all local models
REM echo [WARN] Clearing Ollama model cache...
REM rmdir /s /q "%USERPROFILE%\.ollama"

REM =====================================================
REM DONE
REM =====================================================
echo.
echo ================================================
echo  CLEAN RESET COMPLETE
echo ================================================
echo.
echo Logs archived under:
echo   %ARCHIVE_ROOT%
echo.
echo Press any key to start the dev environment...
echo.

endlocal
pause

REM =====================================================
REM Auto-launch dev environment
REM =====================================================
start_dev.bat