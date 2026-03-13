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
timeout /t 2 >nul
tasklist | findstr /i "ollama.exe" >nul
if not errorlevel 1 (
  echo [WARN] Ollama still running – forcing stop
  taskkill /f /im ollama.exe >nul 2>&1
) else (
  echo [OK]  Ollama process stopped
)

REM =====================================================
REM 3) Wait for port to be free
REM =====================================================
echo [INFO] Waiting for port %OLLAMA_PORT% to be released...
powershell -Command ^
"for ($i=0; $i -lt 10; $i++) {
  $c = Get-NetTCPConnection -LocalPort %OLLAMA_PORT% -ErrorAction SilentlyContinue
  if (-not $c) { exit 0 }
  Start-Sleep -Seconds 1
}
Write-Host 'Port still in use.'; exit 1" ^
|| echo [WARN] Port %OLLAMA_PORT% still appears busy

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
echo Next steps:
echo   1) Review / zip archived logs if needed
echo   2) Run start_dev.bat for a clean session
echo.

endlocal
pause