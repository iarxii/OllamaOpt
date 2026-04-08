# OllamaOpt Rich CLI Quick Start Guide

Welcome to the **OllamaOpt Rich CLI** — a sophisticated Claude/Gemini-style interface for local Ollama models with comprehensive metrics and real-time performance monitoring.

## 🚀 Quick Start

### Prerequisites

- ✅ Ollama running locally on port 11434
- ✅ At least one model pulled (e.g., `ollama pull qwen3.5:9b`)
- ✅ Python 3.8+ with .venv activated
- ✅ Required libraries: `rich`, `requests`, `psutil`

### Installation

1. **Install dependencies** (if not already installed):
   ```bash
   pip install rich requests psutil
   ```

2. **Start Ollama server** (if not already running):
   ```bash
   ollama serve
   ```

3. **Launch the CLI**:
   
   **Option A - Windows Batch Launcher (Recommended):**
   ```bash
   run_ollama_cli.bat
   ```
   
   **Option B - Direct Python:**
   ```bash
   python -m cli.ollama_cli
   ```
   
   **Option C - With custom API endpoint:**
   ```bash
   python -m cli.ollama_cli --api http://localhost:11434
   ```

## 📊 Dashboard Overview

The CLI displays a comprehensive dashboard with real-time metrics:

```
┌─────────────────────────────────────────────────────┐
│  🦙  OLLAMA OPT - Local LLM Intel GPU Optimization  │
│     Status: Connected | Model: qwen3.5:9b           │
│     Hardware Tier: 🚀 GPU                           │
└─────────────────────────────────────────────────────┘

⚡ 45.3ms | 18.5t/s | CPU:35.2% | VRAM:62.1% | ⏱ 5m 23s
```

### Key Metrics Explained

| Metric | Meaning | Good Range |
|--------|---------|-----------|
| **Latency (ms)** | Response time for API calls | <300ms |
| **t/s** | Tokens per second (generation speed) | >15 t/s |
| **CPU%** | System CPU utilization | <70% |
| **VRAM%** | Video RAM usage percentage | <75% |
| **Uptime** | Session duration | ∞ |

### Status Colors

- 🟢 **Green**: Excellent performance
- 🟡 **Yellow**: Good performance  
- 🔴 **Red**: Poor/degraded performance

## 💬 Chat Interface

### Basic Usage

1. Type your message at the prompt (`→ You:`) and press `Enter`
2. The AI responds with tokens streaming in real-time
3. Chat history is maintained for the entire session
4. Use `SHIFT+ENTER` for multi-line input

### Message Display

**User messages** (right-aligned):
```
┌─ You 
│ What is machine learning?
└─
```

**Assistant messages** (left-aligned):
```
┌─ Assistant 
│ Machine learning is a subset of artificial intelligence...
│ It enables systems to learn and improve from experience...
└─
```

## ⌨️ Available Commands

Type any of these commands at the prompt:

### `/help`
Show all available commands and their descriptions.

### `/models`
List all downloaded models with their sizes and load status.

```
Available Models
Model               Size      Status
qwen3.5:9b         6.3 GB    Loaded
llama3.1:latest    4.9 GB    Available
deepseek-r1:7b     8.2 GB    Available
```

### `/switch <model_name>`
Switch to a different model.

```
→ /switch llama3.1:latest
✓ Switched to model: llama3.1:latest
```

### `/stats`
Show detailed session statistics with performance metrics.

```
Session Metrics
Model:           qwen3.5:9b
Size:            6.3 GB
Quantization:    q4_0
Hardware:        GPU - Intel Arc GPU (GPU Detected)
Avg Latency:     87.3ms
Latency Trend:   ↓ (Improving)
CPU Usage:       42.1%
VRAM Usage:      4.2/16.0 GB (26.3%)
Messages:        12
Tokens Generated: 845
Session Duration: 8m 34s
```

### `/info`
Show current model and system information.

### `/clear`
Clear the chat message history.

```
→ /clear
✓ Chat history cleared
```

### `/exit` or `/quit`
Exit the CLI gracefully.

## 🎯 Use Cases & Tips

### Tip 1: Switching Models
When you want to compare different models:
```
→ /switch qwen3.5:9b
✓ Switched to model: qwen3.5:9b

→ How does X work?
[Response from qwen...]

→ /switch llama3.1:latest  
✓ Switched to model: llama3.1:latest

→ How does X work?
[Response from llama...]
```

### Tip 2: Monitoring Performance
Use `/stats` to see if performance is degrading:
- **Latency increasing?** Model may be overheating or system load is high
- **CPU high?** System resources constrained
- **VRAM high?** Close other applications

### Tip 3: Multi-line Input
For complex prompts, use `SHIFT+ENTER`:
```
→ Analyze this code and explain:
│ def fibonacci(n):
│     if n <= 1:
│         return n
│     return fib(n-1) + fib(n-2)
│ [Press ENTER to send]
```

### Tip 4: Response Quality
If responses are too short:
- Try asking more specific questions
- Use `/switch` to try different models
- Check `/stats` — latency spikes cause truncated responses

## 🔧 Hardware Detection

The CLI automatically detects your hardware tier:

- 🚀 **NPU**: Intel Core Ultra AI Boost (fastest, for ≤3.2B models)
- ⚡ **GPU**: Intel Arc, Iris Xe, or dedicated GPU (fast, for 7B-14B models)
- 🐢 **CPU**: CPU-only fallback (reliable for any size)

Current tier is displayed in the header.

## 📈 Performance Optimization

### For Better Performance:
1. **Close other applications** to reduce CPU/memory pressure
2. **Use smaller models** (3.5B) for faster responses
3. **Monitor /stats** — if VRAM >80%, consider restarting
4. **Check latency trend** — `↓` is good, `↑` indicates degradation

### Real-Time Monitoring:
Watch the dashboard metrics update live. The latency bar shows:
- **Green**: <100ms (excellent)
- **Yellow**: 100-300ms (good)
- **Orange**: 300-500ms (fair)
- **Red**: >500ms (poor)

## 🐛 Troubleshooting

### "No models available" on startup
```
✗ No models found. Please pull a model first.
  Example: ollama pull qwen3.5:9b
```
**Solution**: Pull a model using the Ollama CLI before starting the Rich CLI.

### Connection refused (Ollama server not running)
```
[WARN] Ollama server may not be running on port 11434
```
**Solution**: Start Ollama server in another terminal: `ollama serve`

### Streaming stops mid-response
```
✓ Response interrupted
```
**Solution**: Session interrupted. Press `CTRL+C` and try again, or use `/clear` to reset.

### High latency (>1000ms)
**Causes**:
- System under heavy load
- Model too large for available resources
- Ollama internal issue

**Solution**: Use `/stats` to check resources, consider switching to a smaller model.

### Model takes long to load
**Note**: First message after switching models may have a long latency as the model loads. Subsequent messages will be faster.

## 🎨 Customization

### Future Enhancements (Roadmap)
- [ ] Custom color themes
- [ ] Chat history export to Markdown
- [ ] Benchmarking mode within CLI
- [ ] Context window visualization
- [ ] Custom system prompts

## 📝 Examples & Workflows

### Workflow 1: Quick Question
```
→ What is the capital of France?
[Streaming response...]

→ /exit
```

### Workflow 2: Code Analysis
```
→ /models
[View available models...]

→ /switch deepseek-r1:7b
✓ Switched to model: deepseek-r1:7b

→ [Paste code here for analysis]
[Response with 🚀 reasoning...]

→ /stats
[View performance metrics]
```

### Workflow 3: Performance Benchmarking
```
→ /stats
[Initial metrics recorded]

→ [Run several conversational prompts]

→ /stats
[Compare metrics - check improvement/degradation]
```

## 🆘 Support & Documentation

For more information:
- Ollama docs: https://github.com/ollama/ollama
- Model list: https://ollama.ai/library

## 📄 File Structure

```
OllamaOpt/
├── cli/
│   ├── __init__.py                 # Package initialization
│   ├── ollama_cli.py               # Main CLI application
│   ├── metrics_collector.py        # Metrics polling & collection
│   ├── dashboard.py                # Dashboard rendering
│   ├── chat_interface.py           # Chat & streaming handler
│   ├── formatters.py               # Text & response formatting
│   └── assets/
│       └── logo_art.py             # ASCII art & visual assets
├── run_ollama_cli.bat              # Windows launcher
├── docs/
│   └── CLI_QUICKSTART.md           # This file
└── README.md                       # Project overview
```

## 💡 Tips for Best Experience

1. **Use in Full Screen** for best dashboard display
2. **Keep Ollama Running** in a separate terminal
3. **Monitor Metrics** with `/stats` if performance seems off
4. **Clear History** periodically if session gets large (`/clear`)
5. **Experiment** — try different models and compare responses

---

**Enjoy using OllamaOpt Rich CLI! 🚀**
