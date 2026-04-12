## Research Summary & Implementation Plan

### Key Findings

**TurboQuant** (from the paper in your docs/research folder):
- **Approach**: Random rotation → coordinates follow Beta distribution → independent scalar quantization per coordinate
- **Two-stage inner product quantizer**: MSE quantizer (b-1 bits) + 1-bit QJL on residual
- **Results**: 3.5 bits/channel = "absolute quality neutrality", 5x+ KV cache compression
- **Why it works**: Near-independence of coordinates in high dimensions after rotation

**RotorQuant** (GitHub unavailable, likely similar "rotor" approach to random rotation)

### Current Pipeline Analysis

Your pipeline is a **client-side context orchestration layer** that:
- Builds prompts from RAG, memory, tools, history with character budgets
- Uses simple **truncation-based compression** (no LLM-based summarization)
- Does NOT directly control Ollama's internal KV cache (which lives in the server process)

### Critical Realization

**Direct KV cache quantization cannot be implemented** because:
1. The KV cache lives inside the Ollama server process
2. Ollama doesn't expose KV cache manipulation APIs to clients
3. This is a client-side orchestration tool, not a model server

### What We CAN Optimize

| Optimization | Description | Potential Impact |
|--------------|-------------|-------------------|
| **Smart Context Truncation** | Replace simple truncation with importance-based eviction (keep first + last + salient tokens) | 20-30% context efficiency |
| **Streaming Token Estimation** | Better token counting before sending to Ollama | Avoid context overflow |
| **Context Budget Profiles** | Pre-defined budgets optimized per model (DeepSeek-R1 vs Llama-3.2) | Model-specific tuning |
| **Attention-Based Pruning** | Score chunks by relevance to current query, evict low-scoring | Higher effective context density |
| **Compression Pipeline** | Add LLM-based summarization for long context before sending | 2-5x effective context expansion |

### Recommended Implementation

**Phase 1** (Quick wins):
1. Add sliding-window context assembly (keep system + recent + compress middle)
2. Implement token-accurate budgeting using tiktoken or similar
3. Add model-specific context profiles

**Phase 2** (Higher impact):
1. Integrate lightweight summarization for overflow handling
2. Add importance scoring for context eviction decisions

Would you like me to detail any of these optimization approaches for implementation in Act mode?