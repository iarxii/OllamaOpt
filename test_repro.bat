@echo off
setlocal enabledelayedexpansion
set MODEL=qwen3.5:9b
if exist "docs" (
    echo [INFO] Tier 1: Attempting NPU Acceleration...
    for /f "tokens=*" %%i in ('powershell -Command "echo test" 2^>nul') do set BLOB_PATH=%%i
    echo !BLOB_PATH!
)
