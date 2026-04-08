@echo off
setlocal
cd /d "%~dp0"

REM This script now delegates to the smart pipeline.
call run_pipeline.bat

endlocal
