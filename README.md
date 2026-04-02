# OllamaOpt - Unified Intel AI Optimizer

This repository provides tools and scripts to optimize **Ollama** and **Local LLMs** on **Intel AI PCs** (Intel Core Ultra processors). It enables a multi-tier acceleration strategy leveraging the **NPU**, **GPU**, and **CPU**.

## 🚀 Acceleration Tiers

| Tier | Engine | Hardware | Best For | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | **NPU (AI Boost)** | Intel Core Ultra (LNL, MTL, ARL) | Ultra-efficiency, DeepSeek-R1-7B, Llama-3.2 | **Recommended** |
| **Tier 2** | **GPU (Vulkan)** | Intel Arc / Iris Xe Graphics | Large models, General compatibility | Experimental |
| **Tier 3** | **CPU (Default)** | All Intel Processors | Robustness / Fallback | Stable |

## 🛠️ Getting Started

### 1. Run Diagnostics
Check your hardware readiness, driver versions, and compute libraries.
```cmd
run_gpu_diagnostics.bat
```
*Note: The script now automatically detects **Arrow Lake**, **Meteor Lake**, and **Lunar Lake** generations.*

### 2. Launch Optimized Models
Use the "Smart Launcher" to automatically pick the best acceleration tier for your hardware and model.
```cmd
run_intel_optimized.bat deepseek-r1:7b
```

## 🔋 NPU Optimization (Tier 1)
For the highest performance and lowest power usage, we utilize the **IPEX-LLM** NPU-optimized build.
- **Requirements**: NPU Driver **32.0.100.3104+**.
- **Supported Models**: Meta-Llama-3.2, DeepSeek-R1 (1.5B/7B).
- **Guide**: See [NPU_QUICKSTART.md](docs/NPU_QUICKSTART.md).

## 🛠️ GPU Recovery (Tier 2)
If your Intel GPU is not properly offloading, the project includes a **Vulkan** fallback.
- **Quick Fix**: Run `run_intel_optimized.bat` with any model; it will automatically set `OLLAMA_VULKAN=1` if Tier 1 is unavailable.
- **Drivers**: If `igcsycl.dll` or `ze_intel_gpu.dll` are missing, perform a clean driver installation. See [Solution Section](#solution).

---

## 🔧 Solution: Clean Driver Installation
If diagnostics show "NOT FOUND" for critical libraries:
1.  **Download Intel DSA**: [Intel Support Assistant](https://www.intel.com/content/www/us/en/support/detect.html).
2.  **Clean Uninstall**: Remove existing graphics drivers from Windows Apps & Features.
3.  **Install & Reboot**: Install the latest Arc drivers and restart.
4.  **Verify**: Run `run_gpu_diagnostics.bat` again.

---
*Powered by Intel Core Ultra & OllamaOpt*
