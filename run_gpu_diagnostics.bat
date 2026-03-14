@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

powershell -NoProfile -NoLogo -ExecutionPolicy Bypass -File "gpu_diagnostics.ps1"

pause
