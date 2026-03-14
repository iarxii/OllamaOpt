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
```

### 2️⃣ Ensure Ollama is installed
Download and install [Ollama](https://ollama.ai) for Windows.

### 3️⃣ Pull a model (first time only)
```bash
ollama pull qwen3.5:9b
```
Or use any compatible GGUF model (see Recommended Models above).

### 4️⃣ Run the launcher
Double-click or run:
```bash
start_dev.bat
```

This will:
- Create a Python virtual environment (if needed)
- Verify dependencies
- Launch the optimized Ollama server
- Run benchmarks automatically
- Capture logs and metrics

---

## 📋 Script Reference

### **Main Launcher: `start_dev.bat`**
**Purpose**: Development startup with preflight checks and venv setup

**Flow**:
1. Checks Python is installed
2. Creates `.venv/` if missing
3. Installs required packages (`ollamabench`)
4. Verifies Ollama CLI is available
5. Calls `start_qwen35_ollama_with_logging.bat`

**Use when**: You want a full fresh start with dependency verification

```bash
start_dev.bat
```

---

### **Benchmark Launcher: `start_qwen35_ollama_with_logging.bat`**
**Purpose**: Runs Ollama server + benchmarks + latency tests in parallel terminals

**Spawns 3 child windows**:
1. **Ollama Server** - Runs `ollama serve` with Intel GPU optimization
   - Environment: `OLLAMA_NUM_GPU=999`, `ZES_ENABLE_SYSMAN=1`, `SYCL_CACHE_PERSISTENT=1`
   - Logs: `logs\ollama-server.log`, `logs\ollama-debug.log`

2. **Benchmark Runner** - Executes 4 performance tests once API is ready
   - Waits for API via `wait_for_api.ps1`
   - Runs `ollamabench` with 2 warmup runs
   - Logs: `logs\benchmark-qwen39.txt`

3. **Latency Probe** - Measures response latency via `latency_probe.ps1`
   - Logs: `logs\curl-latency.log`

**Use when**: You want to run benchmarks (fastest option, assumes dependencies are installed)

```bash
start_qwen35_ollama_with_logging.bat
```

---

### **Clean Reset: `start_clean.bat`**
**Purpose**: Safely stops Ollama, archives logs, clears active logs

**Steps**:
1. Graceful Ollama shutdown via `ollama stop all`
2. Force-kill `ollama.exe` if still running
3. Verifies port 11434 is released
4. Archives previous logs to `logs_archive\logs_TIMESTAMP\`
5. Clears `logs\` directory

**Use when**: Starting fresh session, previous run is hanging, or need to preserve logs

```bash
start_clean.bat
```

**Then run**:
```bash
start_dev.bat
```

---

### **Kill Ollama: `kill_ollama.bat`**
**Purpose**: Quickly terminates all Ollama processes without archiving logs

**Steps**:
1. Graceful shutdown via `ollama stop all`
2. Force-kill `ollama.exe` if needed
3. Verifies port 11434 is free

**Use when**: You just need to stop Ollama fast (e.g., port conflict)

```bash
kill_ollama.bat
```

---

## 🛠️ Helper Scripts

### `wait_for_api.ps1`
Waits for Ollama API to respond at `http://localhost:11434/api/tags` (max 10 retries)

Called by: `run_wait_for_api.bat` → benchmark launcher

### `latency_probe.ps1`
Measures time to generate response for a given model. Outputs JSON metrics including:
- `timestamp`
- `model`
- `duration` (milliseconds)

Called by: `run_latency_probe.bat` → latency probe window

### `run_wait_for_api.bat` & `run_latency_probe.bat`
Batch wrappers that safely invoke PowerShell scripts from child cmd windows

---

## 📊 Execution Options & Scenarios

### **Scenario 1: Full Fresh Start (Recommended)**
```bash
start_dev.bat
```
**Best for**: First run, new Python environment, or dependency changes
- Creates venv
- Installs packages
- Runs full benchmark suite
- Captures all metrics

---

### **Scenario 2: Quick Benchmark (No Venv Check)**
```bash
start_qwen35_ollama_with_logging.bat
```
**Best for**: Rapid iteration, regression testing
- Assumes venv exists (`start_dev.bat` was run once)
- Launches Ollama + benchmarks immediately
- Faster startup

---

### **Scenario 3: Clean Slate + Full Run**
```bash
start_clean.bat
```
Will Run:
```bash
start_dev.bat
```
**Best for**: Preserving logs, starting fresh, GPU issues
- Stops previous runs
- Archives old logs with timestamp
- Clears working directory
- Full fresh benchmark

---

### **Scenario 4: Emergency Stop**
```bash
kill_ollama.bat
```
**Best for**: Port conflicts, hung processes
- Quick process termination
- No log archiving
- Frees port 11434

---

## 📁 Output & Logs

All logs are written to `logs/` directory:

| File | Purpose |
|------|---------|
| `ollama-server.log` | Ollama server output |
| `ollama-debug.log` | Ollama debug output + errors |
| `benchmark-qwen39.txt` | Full benchmark results (JSON) |
| `curl-latency.log` | Latency probe metrics (JSON) |
| `env.txt` | Environment variables snapshot |

**Archived logs**: `logs_archive/logs_TIMESTAMP/` (created by `start_clean.bat`)

### Sample Benchmark Output
```json
{
  "timestamp": 1773445653.4467456,
  "model": "qwen3.5:9b",
  "overall_metrics": {
    "average_tokens_per_second": 3.23,
    "average_time_to_first_token_ms": 22861.05,
    "benchmark_score": 3.23
  },
  "tasks": [
    {
      "task_name": "Short Summary",
      "tokens_per_second_overall": 4.22,
      "time_to_first_token_ms": 21583.92
    }
    ...
  ]
}
```

---

## 🔧 Customization

### Change Model
Edit `start_qwen35_ollama_with_logging.bat`:
```batch
set "MODEL=llama3.1:latest"
```

Then run:
```bash
start_dev.bat
```

### Change Warmup Runs
Edit `start_qwen35_ollama_with_logging.bat`, find:
```batch
python -m ollamabench.benchmark_runner %MODEL% --warmup-runs 2
```

Change `--warmup-runs 2` to your desired count.

### Adjust GPU Offload
Edit `start_qwen35_ollama_with_logging.bat`:
```batch
set OLLAMA_NUM_GPU=999
```
- `999` = Force all layers to GPU
- `N` = Offload N layers to GPU
- `0` = CPU only (not recommended)

---

## ⚙️ Requirements Detail

### Python Packages
- `ollamabench` - Performs the benchmark suite

Installed automatically by `start_dev.bat`

### System Requirements
- **OS**: Windows 10/11
- **GPU**: Intel Arc or Intel Core Ultra (iGPU)
- **RAM**: ≥16 GB (6-8 GB for model, rest for system)
- **Storage**: ≥20 GB free (varies by model size)
- **Network**: Ollama server runs locally (no internet required)

---

## 🐛 Troubleshooting

### Port 11434 Already in Use
**Symptom**: "listen tcp 127.0.0.1:11434: bind: Only one usage..."

**Fix**:
```bash
kill_ollama.bat
```
Then try again.

### Model Not Found
**Symptom**: "model 'qwen3.5:9b' not found"

**Fix**: Pull the model first
```bash
ollama pull qwen3.5:9b
```

### Venv Issues
**Symptom**: Python package import errors

**Fix**:
```bash
start_dev.bat
```
This recreates the venv and reinstalls dependencies.

### Ollama CLI Not Found
**Symptom**: "Ollama not found in PATH"

**Fix**: Reinstall Ollama or add to PATH manually
```bash
set PATH=%PATH%;C:\Users\<USERNAME>\AppData\Local\Programs\Ollama
```

---

## 📈 Performance Tips

1. **Close unnecessary apps** - Free up RAM for model + OS
2. **Use Q4_K_M quantization** - Best quality/speed tradeoff for Intel
3. **Run at off-peak times** - Avoid background updates/scans
4. **Monitor temps** - Throttling occurs at ~90°C on Intel Arc
5. **Check logs** - `logs/ollama-debug.log` shows GPU usage

---

## 📝 License

MIT - See LICENSE file

---

## 🤝 Contributing

Issues and PRs welcome!

**Report bugs**: GitHub Issues
**Suggest features**: GitHub Discussions