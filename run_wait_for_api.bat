@echo off
REM Wrapper for wait_for_api.ps1
setlocal EnableDelayedExpansion
cd /d "%~dp0"

powershell -NoProfile -NoLogo -ExecutionPolicy Bypass -File "wait_for_api.ps1" %*
exit /b %ERRORLEVEL%
