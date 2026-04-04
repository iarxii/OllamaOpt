# 🦙 Ollama Command Reference

This guide provides a comprehensive list of commands for managing and interacting with local LLMs via Ollama.

## 🛠️ Core Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| `ollama run <model>` | Pull (if missing) and run a model interactively. | `ollama run llama3.2:3b` |
| `ollama pull <model>` | Download a model from the registry without running it. | `ollama pull mistral` |
| `ollama list` | List all models currently installed on your system. | `ollama list` |
| `ollama ps` | List models that are currently loaded into memory. | `ollama ps` |
| `ollama rm <model>` | Remove a model from your local storage. | `ollama rm llama2` |
| `ollama show <model>` | Show detailed information about a model (license, parameters, etc). | `ollama show llama3.2 --parameters` |
| `ollama cp <src> <dest>` | Create a copy of a model (useful for renaming). | `ollama cp llama3 llama3-backup` |
| `ollama serve` | Start the Ollama server manually (useful for background services). | `ollama serve` |
| `ollama stop <model>` | Unload a running model from memory. | `ollama stop llama3.2` |

## 🏗️ Advanced & Development

| Command | Description | Example |
| :--- | :--- | :--- |
| `ollama create <name> -f <file>` | Create a new model from a `Modelfile`. | `ollama create my-model -f ./Modelfile` |
| `ollama push <model>` | Push a custom model to the Ollama registry (requires login). | `ollama push user/model` |

## 🚀 Optimized Multi-Tier Accelerator (Intel)

Use the automated launcher for the best experience on your AI PC:

| Command | Description |
| :--- | :--- |
| **`./run_intel_optimized.bat <model>`** | **Auto-Booster**: Automatically selects NPU (<=3.2B) or GPU (>3.2B) for max speed. |
| `./run_intel_optimized.bat <model> --force-gpu` | Force the model onto the **iGPU/dGPU** (Vulkan Power Tier). |
| `./run_intel_optimized.bat <model> --force-npu` | Force the model onto the **NPU** (Efficiency AI Boost Tier). |
| `powershell -File gpu_diagnostics.ps1` | Report concurrent NPU and iGPU utilization metrics. |

## ⚙️ Intel Optimization Environment Variables

When using the `run_intel_optimized.bat` launcher, it automatically sets these for you, but you can also use them manually:

| Variable | Value | Purpose |
| :--- | :--- | :--- |
| `OLLAMA_VULKAN` | `1` | Enables Vulkan acceleration for Intel Arc/Xe GPUs. |
| `OLLAMA_NUM_GPU` | `999` | Forces all layers onto the GPU (if memory allows). |
| `ZES_ENABLE_SYSMAN` | `1` | Required for Intel System Management (NPU/GPU diagnostics). |
| `SYCL_CACHE_PERSISTENT` | `1` | Speeds up subsequent loads on Intel hardware. |

## 💡 Pro Tips

-   **Model Versions**: Use tags to specify versions (e.g., `llama3:7b-instruct-q4_K_M`). If no tag is provided, `latest` is assumed.
-   **Exiting**: While in an interactive session (`ollama run`), type `/bye` to exit.
-   **API Access**: Ollama runs a REST API on `http://localhost:11434` by default.
-   **Model Location**: On Windows, models are stored in `%USERPROFILE%\.ollama\models` by default.
