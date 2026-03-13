# OllamaOpt – Local LLM Intel GPU Optimization Script

**OllamaOpt** is a Windows-first optimization, benchmarking, and logging toolkit for running **local Large Language Models (LLMs)** via **Ollama** with **Intel GPU acceleration** (Intel Arc / Intel Core Ultra iGPU).

The project provides a **one‑click `.bat` launcher** that:
- Forces **full GPU layer offload** on Intel hardware
- Enables **debug‑level runtime logging**
- Runs **repeatable benchmarks** (tokens/sec, TTFT)
- Captures **latency probes** and environment snapshots
- Works seamlessly with **VS Code, Copilot, Continue, OpenWebUI**, or direct API usage

---

## 🎯 Project Goals

- ✅ Maximize performance of local LLMs on **Intel GPUs**
- ✅ Eliminate silent CPU fallback
- ✅ Provide **evidence-based tuning** (logs + benchmarks)
- ✅ Support **agentic coding** and long-running sessions
- ✅ Keep everything **local, private, and reproducible**

---

## 🧠 What This Project Optimizes

| Area | What OllamaOpt Does |
|---|---|
| GPU Offload | Forces **all model layers** onto Intel GPU |
| Stability | Prevents memory thrashing & partial CPU fallback |
| Observability | Captures **debug, benchmark, and latency logs** |
| Repeatability | Same startup, same environment, every run |
| Tooling | Works with VS Code Copilot / local LLM clients |

---

## 🧩 Supported Use Cases

- Local coding assistants (Qwen / DeepSeek / Llama)
- Agentic workflows (tool calling, repo reasoning)
- Performance tuning & regression testing
- Evidence for hardware or driver changes
- Governance / audit‑friendly local AI setups

---

## 🖥️ Requirements

### Hardware
- Intel Arc GPU **or**
- Intel Core Ultra (iGPU with shared VRAM)
- ≥ 16 GB system RAM (recommended)

### Software
- Windows 11
- Python 3.10+
- Conda (Anaconda / Miniconda)
- Ollama installed
- Intel GPU drivers up to date

---

## 📦 Recommended Models

Optimized for laptops and Intel GPUs:

- `qwen3.5:8B` (reasoning + coding)
- `qwen2.5-coder:7B`
- `deepseek-coder:6.7B`
- Any GGUF Q4 / Q5 quantized model

---

## 🚀 Quick Start

### 1️⃣ Clone or download the project
```bash
git clone https://github.com/iarxii/OllamaOpt
cd OllamaOpt