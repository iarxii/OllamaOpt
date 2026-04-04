# Intel AI PC LLM Optimization Guide (OllamaOpt)

This repository contains tools to maximize LLM performance on Intel Core Ultra processors (Meteor Lake, Arrow Lake, Lunar Lake) by leveraging both the **NPU (Intel AI Boost)** and the **Integrated/Discrete GPU**.

## 🚀 Smart Routing (v2.0)

The new `run_intel_optimized.bat` launcher now acts as an intelligent orchestrator. It automatically selects the fastest accelerator for your model to minimize system overhead.

### Default Logic:
| Model Size | Accelerator | Use Case |
|------------|-------------|----------|
| **<= 3.2B** | **NPU** (Tier 1) | Ultra-efficiency, low power, keeps system quiet. |
| **> 3.2B** | **GPU** (Tier 2) | Maximum throughput for complex reasoning and large weights. |

---

## 🛠️ Usage

### Automatic (Recommended)
```bash
./run_intel_optimized.bat llama3.2:3b
```
The script will analyze the modelfile and pick the best path.

### Manual Overrides
Force a specific device if you want to compare performance:
- **Force GPU**: `./run_intel_optimized.bat llama3.2:3b --force-gpu`
- **Force NPU**: `./run_intel_optimized.bat qwen3.5:9b --force-npu`

---

## 📊 Monitoring the "AI Booster"

Use our diagnostic tool to see both accelerators working in tandem:
```bash
powershell -ExecutionPolicy Bypass -File gpu_diagnostics.ps1
```
The diagnostics will now report:
- **iGPU Active Memory** (VRAM usage)
- **NPU Utilization Percentage**

---

## 🔧 Environment Configuration

The following flags are automatically managed by the launcher but can be adjusted in `run_intel_optimized.bat`:
- `IPEX_LLM_NPU_ARL=1`: Specifically for Arrow Lake (Ultra 2xx).
- `IPEX_LLM_NPU_MTL=1`: Specifically for Meteor Lake (Ultra 1xx).
- `OLLAMA_VULKAN=1`: Ensures Intel graphics are used for offloading in Tier 2.
