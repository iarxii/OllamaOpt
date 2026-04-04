# Implementation Plan - Intel 'AI Booster' (Hybrid Accelerator) Workflow

This plan addresses your request to use the Intel NPU as an "AI Booster" alongside the GPU, rather than exclusively. Currently, the industry-standard tools for Intel AI PCs (`ipex-llm` and `llama-cpp-npu`) treat these accelerators as mutual exclusives for a single inference process.

## User Review Required

> [!IMPORTANT]
> **Simultaneous NPU + GPU Limitation:** Current stable builds of `ipex-llm` and `llama.cpp` for Windows do **not** support splitting a single model's layers across the NPU and GPU simultaneously (Hybrid Parallelism). 
> 
> The architecture is designed to offload to **one** primary accelerator to avoid the massive latency overhead of moving tensors between the NPU and iGPU/dGPU memory pools.

## Proposed Strategy: "Smart Orchestration"

Instead of trying to force a single model onto both devices (which would likely be slower due to syncing overhead), we will implement a **Dual-Engine Orchestration** strategy:

### 1. Unified Intel Booster Launcher
Update `run_intel_optimized.bat` to support an "Auto-Booster" mode that intelligently selects the accelerator based on model architecture and memory requirements:
- **Efficiency Boost (NPU)**: For models < 4B (e.g., `llama3.2:3b`). This preserves GPU life and battery for other system-intensive tasks.
- **Power Boost (GPU)**: For models > 7B (e.g., `qwen3.5:9b`). This utilizes the higher TFLOPS of your Intel graphics hardware via Vulkan.

### 2. Multi-Process Concurrency
The "Booster" workflow means you can run **two models simultaneously**:
- One on the **NPU** via our launcher for a persistent, background assistant.
- One on the **GPU** via Ollama for code-heavy reasoning tasks.
This is the true "Booster" experience for an AI PC.

---

## Proposed Changes

### [Component Name] Smart Launcher

#### [MODIFY] [run_intel_optimized.bat](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/run_intel_optimized.bat)
- Implement a threshold-based routing system based on model size.
- Add support for `-vulkan` or `-npu` manual overrides.
- **Fix Regression**: Ensure the `-kv` flag is removed (already done in a hotfix).

### [Component Name] GPU/NPU Calibration

#### [MODIFY] [gpu_diagnostics.ps1](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/gpu_diagnostics.ps1)
- Add a "Booster Readiness" check that reports the available memory on both the NPU and GPU concurrently.

---

## Open Questions

1. **Integrated vs Discrete**: Do you have a discrete Arc GPU (e.g., A770/A370M) or just the integrated Intel Graphics on your Ultra processor? This affects whether we should prioritize the GPU for large models.
2. **Workflow Priority**: Is your priority **throughput for one model**, or **system responsiveness** where the NPU handles the conversation so your GPU stays free for rendering your IDE and UI?

## Verification Plan

### Automated Tests
- `run_intel_optimized.bat llama3.2:3b` -> Should trigger NPU (Efficiency).
- `run_intel_optimized.bat qwen3.5:9b` -> Should trigger GPU (Vulkan) automatically.

### Manual Verification
- Monitor Task Manager (Performance tab) to verify both chips are being utilized correctly across your workflow.
