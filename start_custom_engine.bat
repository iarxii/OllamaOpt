@echo off
SETLOCAL EnableDelayedExpansion

echo ==========================================================
echo  Starting Custom RotorQuant Engine (llama.cpp)
echo ==========================================================
echo.

:: Get the model blob path using the find script
for /f "delims=" %%i in ('powershell -ExecutionPolicy Bypass -File ".\find_ollama_model.ps1" -ModelName "qwen2.5-coder:3b"') do set MODEL_PATH=%%i

if "%MODEL_PATH%"=="" (
    echo [ERROR] Failed to locate the model blob for qwen2.5-coder:3b.
    pause
    exit /b 1
)

echo [INFO] Found model blob: %MODEL_PATH%
echo [INFO] Launching llama-server on port 11434 with 8-bit KV Cache (q8_0) on Vulkan...
echo [INFO] Note: iso4/planar4 kernels are CUDA-only; q8_0 provides best Vulkan stability.
echo.

.\llama-cpp-turboquant\build\bin\Release\llama-server.exe -m "%MODEL_PATH%" --port 11434 --ctx-size 16384 -ngl 99 --embedding --pooling mean -ctk q8_0 -ctv q8_0
