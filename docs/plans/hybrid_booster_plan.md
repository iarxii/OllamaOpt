# Implementation Plan - Intel 'AI Booster' (Hybrid Accelerator) Workflow

This plan addresses your request to use the Intel NPU as an "AI Booster" alongside your **Integrated Intel GPU**, with a focus on **Single Model Max Speed**.

## User Review Required

> [!IMPORTANT]
> **Integrated Memory Contention:** Since your system uses an **Integrated GPU (iGPU)**, both the CPU, GPU, and NPU share the same system memory bandwidth. 
> 
> **The "Max Speed" Strategy:** To achieve the highest T/s (tokens per second), it is usually better to offload the entire model to the GPU for larger models (7B+), as it has significantly more execution units (EUs) and higher throughput than the NPU. We will reserve the NPU for smaller models (<= 3B) where the overhead of the GPU outweighs its benefits.

---

## Proposed Strategy: "Speed-First Orchestration"

We will implement a **Predictive Accelerator Selector** that bypasses trial-and-error by selecting the fastest path based on model metadata.

### 1. Smart Routing Logic
Update `run_intel_optimized.bat` to analyze the model's metadata before launching:
- **Tier 1 (NPU - Efficiency Path)**: DEFAULT for models <= 3.2B. The NPU provides competitive speed with 90% less power consumption, keeping the GPU cool and free for UI rendering.
- **Tier 2 (GPU - Power Path)**: DEFAULT for models > 3.2B. The integrated Intel graphics will handle the heavy computation via Vulkan for maximum raw performance.

### 2. Manual Overrides
Add support for `--force-npu` and `--force-gpu` flags to allow you to manually test and see the T/s difference.

---

## Proposed Changes

### [Component Name] Smart Launcher (v2.0)

#### [MODIFY] [run_intel_optimized.bat](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/run_intel_optimized.bat)
- Implement logic to check model size and route accordingly.
- Add support for `-vulkan` or `-npu` manual overrides.
- Enable high-priority process scheduling for the active model.

### [Component Name] Documentation & Benchmarking

#### [NEW] [README.md](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/docs/README.md)
- Create a comprehensive guide for "Intel AI PC LLM Optimization".

#### [MODIFY] [gpu_diagnostics.ps1](file:///c:/AppDev/OllamaOpt%20-%20Local%20LLM%20Intel%20GPU%20Optimization/gpu_diagnostics.ps1)
- Add bandwidth measurement to help decide where the bottleneck lies.

---

## Verification Plan

### Performance Benchmark
- Compare T/s for Llama 3.2 3B on both Tiers.
- Compare T/s for Qwen 3.5 9B on both Tiers.
