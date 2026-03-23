# Fix GPU Offload Detection and Pipeline Reporting

The pipeline is currently failing because:
1. [gpu_diagnostics.ps1](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/gpu_diagnostics.ps1) check on `/api/show` is not finding the "gpu" string in the static model metadata.
2. `spawn_server.bat` (and others) have inconsistent syntax.
3. The success string `[PASS] GPU offload is ACTIVE!` in [run_pipeline.bat](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/run_pipeline.bat) does not match the PowerShell script's output.

## Proposed Changes

### GPU Diagnostics Improvements

#### [MODIFY] [gpu_diagnostics.ps1](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/gpu_diagnostics.ps1)
- Update the API check to use `/api/ps`. This endpoint returns the *running* models and explicitly shows which processor they are using (CPU/GPU) and the VRAM usage.
- Standardize the success message to: `[SUCCESS] GPU acceleration is ACTIVE!`
- Allow the diagnostic to "PASS" even if `igcsycl.dll` is missing, provided that the API report shows GPU usage (Vulkan fallback).

### Pipeline Verification Fix

#### [MODIFY] [run_pipeline.bat](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/run_pipeline.bat)
- Update the `findstr` command to look for the exact standardized success message: `[SUCCESS] GPU acceleration is ACTIVE!`

### Clean Startup Fixes

#### [MODIFY] [kill_ollama.bat](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/kill_ollama.bat)
Wait, the user made some changes manually too. I should verify them.

## Verification Plan

### Automated Tests
- Run [run_pipeline.bat](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/run_pipeline.bat) and verify that the "SUCCESS" message is correctly detected in the log.
- Check [logs\gpu_diagnostics.log](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/logs/gpu_diagnostics.log) for the "ACTIVE" message.

### Manual Verification
- Ask the user to run the pipeline and confirm that it no longer terminates prematurely.
