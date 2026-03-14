@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM =====================================================
REM OllamaOpt - start_dev.bat
REM - Creates/uses a local Python venv (.venv)
REM - Preflight checks for required executables
REM - Ensures required Python packages are installed
REM - Then launches start_qwen35_ollama_with_logging.bat
REM =====================================================

REM ---- Project root (directory of this script)
set "ROOT=%~dp0"
cd /d "%ROOT%"

REM ---- Config (edit if you want)
set "VENV_DIR=%ROOT%.venv"
set "PYTHON_EXE=python"
set "REQUIRED_PY_PKGS=ollamabench"
set "LAUNCHER_BAT=%ROOT%start_qwen35_ollama_with_logging.bat"

echo.
echo ================================================
echo  OllamaOpt Dev Startup + Preflight
echo  Root: %ROOT%
echo ================================================
echo.

REM =====================================================
REM 1) Preflight: Python present?
REM =====================================================
where %PYTHON_EXE% >nul 2>&1
if errorlevel 1 (
  echo [FAIL] Python not found in PATH.
  echo        Install Python 3.10+ and ensure 'python' is available.
  echo        TIP: reopen terminal after install.
  exit /b 1
)

REM =====================================================
REM 2) Create venv if missing
REM =====================================================
if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [INFO] Creating virtual environment at: %VENV_DIR%
  %PYTHON_EXE% -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [FAIL] Could not create venv.
    exit /b 1
  )
) else (
  echo [OK]  Virtual environment found: %VENV_DIR%
)

REM =====================================================
REM 3) Activate venv
REM =====================================================
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
  echo [FAIL] Could not activate venv.
  exit /b 1
)

REM =====================================================
REM 4) Upgrade pip tooling (safe to re-run)
REM =====================================================
echo [INFO] Upgrading pip/setuptools/wheel...
python -m pip install --upgrade pip setuptools wheel >nul

REM =====================================================
REM 5) Ensure required Python packages are installed
REM =====================================================
echo [INFO] Checking required Python packages...
for %%P in (%REQUIRED_PY_PKGS%) do (
  python -m pip show %%P >nul 2>&1
  if errorlevel 1 (
    echo [INFO] Installing missing package: %%P
    python -m pip install "%%P"
    if errorlevel 1 (
      echo [FAIL] Failed to install package: %%P
      exit /b 1
    )
  ) else (
    echo [OK]  %%P already installed
  )
)

REM =====================================================
REM 6) Preflight: Ollama CLI present?
REM =====================================================
where ollama >nul 2>&1
if errorlevel 1 (
  echo [WARN] Ollama CLI not found in PATH.
  echo        If you installed Ollama via the Windows app, this can still work,
  echo        but the launcher may fail to call 'ollama'.
  echo        Fix: ensure ollama.exe is in PATH or reinstall Ollama.
) else (
  echo [OK]  Ollama CLI detected
)

REM =====================================================
REM 7) Verify launcher exists
REM =====================================================
if not exist "%LAUNCHER_BAT%" (
  echo [FAIL] Launcher not found:
  echo        %LAUNCHER_BAT%
  echo        Ensure start_qwen35_ollama_with_logging.bat exists in the project root.
  exit /b 1
)

REM =====================================================
REM 8) Run the launcher
REM =====================================================
echo.
echo [GO] Launching: %LAUNCHER_BAT%
echo.
call "%LAUNCHER_BAT%"

REM Note: If the launcher opens new terminals, they may not inherit this venv.
REM If you want them to, edit the launcher to activate %VENV_DIR%\Scripts\activate.bat
REM in each 'start cmd /k' block.

endlocal