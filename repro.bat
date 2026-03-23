@echo off
setlocal EnableExtensions EnableDelayedExpansion
echo Testing Batch syntax...

set "TEST_VAR="
if "!TEST_VAR!"=="1" (
  echo Case 1
) else (
  echo Case 2
)

if not exist "logs" echo Logs missing
echo Done.
