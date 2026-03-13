@echo off
REM Wrapper for latency_probe.ps1
setlocal EnableDelayedExpansion
cd /d "%~dp0"

powershell -NoProfile -NoLogo -ExecutionPolicy Bypass -File "latency_probe.ps1" %*
exit /b %ERRORLEVEL%
