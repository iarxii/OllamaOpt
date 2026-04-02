# NPU Quickstart Guide (Intel AI Boost)

This guide helps you leverage the **Intel NPU** (Neural Processing Unit) for ultra-efficient local LLM inference using the **IPEX-LLM** optimized build.

## Prerequisites

1.  **NPU Driver**: Ensure your NPU driver is version **32.0.100.3104** or newer.
    *   Download: [Intel NPU Driver for Windows](https://www.intel.com/content/www/us/en/download/794734/intel-npu-driver-windows.html)
2.  **Hardware**: Requires an **Intel Core Ultra** processor (Meteor Lake, Lunar Lake, or Arrow Lake).
    *   *Your current CPU (Ultra 7 255U) is an Arrow Lake model and is supported.*

## Getting Started

### 1. Model Preparation
The NPU-optimized engine (`llama-cli-npu.exe`) works best with **GGUF** models. You can use your existing Ollama models!
- Recommended models:
  - `deepseek-r1:1.5b`
  - `deepseek-r1:7b`
  - `llama-3.2-3b:latest`

### 2. Using the Automated Launcher
We have provided a "Smart Launcher" that automatically detects your NPU and applies the correct environment flags.

```cmd
run_intel_optimized.bat deepseek-r1:7b
```

### 3. Manual Configuration (Advanced)
If you wish to run the tools manually, set the following environment variables based on your CPU:

- **Arrow Lake (2xxU/H/K)**: `set IPEX_LLM_NPU_ARL=1`
- **Meteor Lake (1xxH)**: `set IPEX_LLM_NPU_MTL=1`
- **Lunar Lake (2xxV)**: `set IPEX_LLM_NPU_DISABLE_COMPILE_OPT=1`

## Current Limitations
- **Sequence Length**: Maximum sequence length is **1024** tokens.
- **Input Tokens**: Maximum input tokens is **960**.
- **Model Support**: Currently restricted to Llama-3.2 and DeepSeek-R1-Qwen variants.

---
*Powered by OllamaOpt & Intel IPEX-LLM*
