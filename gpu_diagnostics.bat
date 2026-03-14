@echo off
setlocal EnableExtensions EnableDelayedExpansion
title OllamaOpt - GPU Diagnostics

cd /d "%~dp0"

echo.
echo ================================================
echo  OllamaOpt - GPU Diagnostics
echo ================================================
echo.

REM =====================================================
REM 1) Check Intel GPU presence
REM =====================================================
echo [INFO] Checking for Intel GPU devices...
wmic path win32_videocontroller get name,pnpdeviceid | findstr /i "intel arc xe" >nul
if errorlevel 1 (
  echo [WARN] No Intel Arc/Xe GPU detected via WMI
) else (
  echo [OK]  Intel GPU detected
  wmic path win32_videocontroller get name,pnpdeviceid | findstr /i "intel"
)

echo.

REM =====================================================
REM 2) Check Intel GPU drivers
REM =====================================================
echo [INFO] Checking Intel GPU driver status...
dxdiag /t dxdiag_output.txt >nul 2>&1
timeout /t 2 >nul 2>&1
if exist dxdiag_output.txt (
  findstr /i "directx" dxdiag_output.txt | head -n 5
  del dxdiag_output.txt
)

echo.

REM =====================================================
REM 3) Test Ollama GPU detection
REM =====================================================
echo [INFO] Testing Ollama GPU detection...
echo.
echo The following should show GPU info if properly configured:
echo.

REM Set Intel GPU environment variables
set OLLAMA_NUM_GPU=999
set ZES_ENABLE_SYSMAN=1
set SYCL_CACHE_PERSISTENT=1
set OLLAMA_DEBUG=1

echo Running: ollama -v (version info)
ollama -v
echo.

echo Running: ollama show qwen3.5:9b (model info - check GPU section)
echo This should show GPU layer offload information:
echo.
ollama show qwen3.5:9b | findstr /i "gpu"

echo.

REM =====================================================
REM 4) Check environment variables
REM =====================================================
echo [INFO] Current environment variables for Intel GPU:
echo.
echo OLLAMA_NUM_GPU=%OLLAMA_NUM_GPU%
echo ZES_ENABLE_SYSMAN=%ZES_ENABLE_SYSMAN%
echo SYCL_CACHE_PERSISTENT=%SYCL_CACHE_PERSISTENT%
echo OLLAMA_DEBUG=%OLLAMA_DEBUG%

echo.

REM =====================================================
REM 5) Check DirectX and GPU capabilities
REM =====================================================
echo [INFO] GPU Capability Test via PowerShell:
echo.
powershell -NoProfile -NoLogo -Command "Get-WmiObject Win32_VideoController | Select-Object Name, DriverVersion, VideoProcessor"

echo.
echo ================================================
echo  Diagnostics Complete
echo ================================================
echo.
echo Interpretation:
echo   - If no Intel GPU listed above: Install Intel Arc drivers
echo   - If Intel GPU listed but no GPU layers: UPDATE drivers
echo   - If GPU layers shown: Intel GPU is properly connected
echo.

endlocal
pause
