@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║     🦙  OllamaOpt Rich CLI - Local LLM Optimization         ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%"

echo [Step 1/4] Checking dependencies...

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

REM Check if .venv exists
if not exist "%PROJECT_DIR%.venv" (
    echo [WARN] Virtual environment not found
    echo [INFO] Creating virtual environment...
    python -m venv "%PROJECT_DIR%.venv"
)

REM Activate virtual environment
echo [Step 2/4] Activating virtual environment...
call "%PROJECT_DIR%.venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

echo [Step 3/4] Installing required packages...

REM Install dependencies silently
python -m pip install -q rich requests psutil 2>nul

REM Verify imports
python -c "import rich, requests, psutil; from cli import ollama_cli" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to import required modules
    echo [INFO] Trying to install dependencies again...
    python -m pip install rich requests psutil
    pause
    exit /b 1
)

echo [Step 4/4] Checking Ollama server...

REM Try to connect to Ollama
python -c "import requests; requests.get('http://localhost:11434/api/tags', timeout=1)" >nul 2>&1
if errorlevel 1 (
    echo [WARN] Ollama server not responding on localhost:11434
    echo [INFO] Make sure Ollama is running: ollama serve
    echo.
) else (
    echo [OK] Ollama server is responding
    echo.
)

echo ═══════════════════════════════════════════════════════════════
echo [OK] Starting OllamaOpt Rich CLI
echo ═══════════════════════════════════════════════════════════════
echo.

REM Launch the CLI
python -m cli.ollama_cli %*

REM Clean up
echo.
echo [INFO] Closing OllamaOpt CLI
deactivate

pause
