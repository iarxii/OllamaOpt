# Implementation Plan - Unified Intel AI Accelerator (NPU & GPU)

The goal is to integrate the specialized **IPEX-LLM NPU-optimized** build of `llama-cpp` (found in `docs\utils\...`) as the primary accelerator for supported models, with a persistent fallback strategy.

## User Review Required

> [!IMPORTANT]
> **Priority Hierarchy**:
> 1. **NPU (Tier 1)**: via `llama-cli-npu.exe`. Most efficient, lowest power/latency.
> 2. **Vulkan GPU (Tier 2)**: via official Ollama server with `OLLAMA_VULKAN=1`. Best for non-NPU supported models.
> 3. **CPU (Tier 3)**: Standard Ollama server.
>
> **NPU Driver Requirement**: Must be **32.0.100.3104** or newer.

> [!NOTE]
> **CPU Detection**: The scripts will automatically detect your CPU generation (**Meteor Lake**, **Lunar Lake**, or **Arrow Lake**) and set the appropriate `IPEX_LLM_NPU_*` flags as required by the build's README.

## Proposed Changes

### 1. Advanced Diagnostics

#### [MODIFY] [gpu_diagnostics.ps1](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/gpu_diagnostics.ps1)
- **NPU Driver Audit**: Detect version `32.0.100.3104`.
- **Generation Detection**: Check WMI for CPU model name (e.g., "155H" -> MTL, "258V" -> LNL).
- **Tool Validation**: Check for `docs\utils\llama-cpp-ipex-llm-2.3.0b20250424-win-npu\llama-cli-npu.exe`.

### 2. Multi-Accelerator Launcher

#### [NEW] [start_intel_optimized.bat](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/start_intel_optimized.bat)
- Detects the requested model.
- Checks hardware via the updated diagnostics.
- Lauch logic:
  - `If (NPU-Compatible Model && NPU-Ready) -> Launch llama-cli-npu.exe`
  - `Else If (GPU-Ready) -> Launch Ollama with OLLAMA_VULKAN=1`
  - `Else -> Launch standard Ollama (CPU)`

### 3. Documentation & Guides

#### [NEW] [docs/NPU_QUICKSTART.md](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/docs/NPU_QUICKSTART.md)
- Summarize the usage instructions for the IPEX-LLM NPU build.

#### [MODIFY] [README.md](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/README.md)
- Add "Unified Acceleration" section.

---

## Open Questions

1. **CPU Info**: What is your exact Intel CPU model (e.g., Ultra 7 155H)?
2. **Model Path**: Do you want the launcher to automatically scan your Ollama models folder to find the GGUF blobs for the NPU tool?

## Verification Plan

### Automated Tests
- Script-based verification of `IPEX_LLM_NPU_*` env var setting.
- WMI query test for NPU driver version.

### Manual Verification
- Testing `start_intel_optimized.bat` with **DeepSeek-R1-7B** and checking NPU usage in Task Manager.
