Absolutely — and given your current hardware and the progress already documented in [Project\_Review\_20260407\_2244.md](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Project_Review_20260407_2244.md?EntityRepresentationId=ad95938d-5452-422e-988f-ac15e174e5b6), [Intel\_GPU\_Optimization\_Exec\_Guide.md](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Intel_GPU_Optimization_Exec_Guide.md?EntityRepresentationId=d4f1a080-1e2b-4431-aa8e-b6172b17b377), [NPU\_QUICKSTART.md](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/NPU_QUICKSTART.md?EntityRepresentationId=5fd3f910-ae0b-436a-af9b-e17fee133fd3), and [CLI\_QUICKSTART.md](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/CLI_QUICKSTART.md?EntityRepresentationId=51db8973-3637-4187-a0e7-d86b342ccc8e), the right move is **not** “build a giant general-purpose agent stack.” The right move is to build a **small-model-first, tool-centric, retrieval-grounded local agent platform**. Your own project notes already show that the strongest path on this machine is **Llama 3.2 3B on the NPU** for short interactions and **DeepSeek-R1 7B / similar 7B-class models on the Intel GPU** for heavier reasoning, while 9B-class interactive use is a poor fit for this device. [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Project_Review_20260407_2244.md), [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/NPU_QUICKSTART.md), [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Intel_GPU_Optimization_Exec_Guide.md)

Below is an **authoritative implementation guideline** that maps directly to your use case.

***

# Agent Guideline for Your Local Intel AI PC Pipeline

## 1) Executive design decision

Your platform should be designed as:

> **A local agent runtime that uses a small local model for orchestration, MCP servers for tool access, RAG for factual grounding, and a lightweight vector store for retrievable memory.**

That direction matches:

*   your hardware reality: [NPU\_QUICKSTART.md](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/NPU_QUICKSTART.md?EntityRepresentationId=5fd3f910-ae0b-436a-af9b-e17fee133fd3) says the NPU path is best with GGUF models such as `llama-3.2-3b:latest`, but it has a **maximum sequence length of 1024** and **maximum input tokens of 960**. [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/NPU_QUICKSTART.md)
*   your project review: [Project\_Review\_20260407\_2244.md](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Project_Review_20260407_2244.md?EntityRepresentationId=ad95938d-5452-422e-988f-ac15e174e5b6) records a real result of **13.04 tok/s on Llama 3.2 3B** on the NPU and recommends focusing on `llama3.2:3b` and `deepseek-r1:7b`, while dropping `qwen3.5:9b` for interactive use on this machine. [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Project_Review_20260407_2244.md)
*   your CLI architecture: [CLI\_QUICKSTART.md](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/CLI_QUICKSTART.md?EntityRepresentationId=51db8973-3637-4187-a0e7-d86b342ccc8e) already assumes a local Ollama-compatible serving layer on port `11434`, model switching, metrics, and hardware-tier awareness. [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/CLI_QUICKSTART.md)

**Conclusion:** your agent stack must be built around **short-context orchestration + external retrieval/tooling**, not around “larger local model knows everything.”

***

## 2) The governing architectural rule

### Rule A — The model must not be the knowledge system

Your local model is for:

*   intent parsing
*   tool selection
*   answer synthesis
*   short reasoning loops

Your local model is **not** the authoritative source of truth.

That is exactly why **RAG** and **MCP** belong in your architecture:

*   **RAG** adds external, up-to-date or private knowledge at query time rather than relying on model memory. Microsoft’s RAG guidance describes RAG as combining retrieval with generation so responses are grounded in enterprise content instead of model memory. [\[learn.microsoft.com\]](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/retrieval-augmented-generation)
*   **MCP** is the protocol layer for standardized access to external tools and data. The official MCP specification states that MCP is an open protocol for connecting LLM applications to external data sources and tools, and the official spec currently exposes multiple specification versions, with the latest stable version listed as `2025-11-25`. [\[modelconte...tocol.info\]](https://modelcontextprotocol.info/specification/)

### Rule B — Retrieval and tool use should carry the factual burden

This is especially important because your NPU path has tight context limits: **1024 sequence / 960 input tokens**. Long prompt stuffing is the wrong pattern on this machine. [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/NPU_QUICKSTART.md)

***

## 3) The architecture you should implement

## Recommended target architecture

### Layer 1 — Inference runtime

Use your existing **Ollama-compatible local serving path** as the model runtime because your CLI already depends on a local server on port `11434`. [CLI\_QUICKSTART.md](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/CLI_QUICKSTART.md?EntityRepresentationId=51db8973-3637-4187-a0e7-d86b342ccc8e) explicitly states that the CLI expects Ollama running locally on that port. [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/CLI_QUICKSTART.md)

Ollama’s official tool support post says Ollama supports tool calling through the `tools` field in its API, and the official llama3.2 library entry describes the 1B/3B models as optimized for multilingual dialogue use cases including **tool use**. [\[ollama.com\]](https://ollama.com/blog/tool-support), [\[ollama.com\]](https://ollama.com/library/llama3.2)

### Layer 2 — Agent orchestration

Use **LangChain / LangGraph-style orchestration** for back-end agent control.

Why this is authoritative:

*   LangChain’s official MCP docs say agents can use tools defined on MCP servers through the `langchain-mcp-adapters` library. [\[docs.langchain.com\]](https://docs.langchain.com/oss/python/langchain/mcp)
*   The same docs state that `MultiServerMCPClient` can connect to multiple MCP servers and is **stateless by default**, with each tool invocation creating a fresh MCP client session. [\[docs.langchain.com\]](https://docs.langchain.com/oss/python/langchain/mcp)

This makes LangChain a strong fit for:

*   multi-tool routing
*   structured control loops
*   RAG integration
*   controlled retries and fallbacks

### Layer 3 — MCP integration

Use MCP as the **standard tool plane**, not as the whole application.

This means:

*   databases, file operations, web search, shell-safe utilities, internal API wrappers, and domain tools should be exposed as MCP servers
*   your orchestration layer should discover and invoke them through MCP clients/adapters

Important honesty point: I found **official evidence for Ollama tool calling**, and **official evidence for LangChain + MCP adapters**, but I did **not** find an official Ollama source in these results claiming that Ollama itself is a native MCP client. The safest architectural interpretation from the sources is:

*   Ollama = inference + tool-calling capable model runtime [\[ollama.com\]](https://ollama.com/blog/tool-support), [\[ollama.com\]](https://ollama.com/library/llama3.2)
*   LangChain / adapters / bridges = MCP connectivity layer [\[docs.langchain.com\]](https://docs.langchain.com/oss/python/langchain/mcp), [\[pypi.org\]](https://pypi.org/project/ollama-mcp-bridge/)

So your architecture should use a **bridge/adapters approach**, not assume native MCP client behavior inside Ollama.

### Layer 4 — Retrieval and memory

Use a lightweight vector store.

The strongest official fit for your hardware is **Qdrant local mode**:

*   LangChain’s official Qdrant integration docs explicitly say Qdrant can run in **local mode, no server required**, and that local mode can be **in-memory** or **on-disk**. [\[docs.langchain.com\]](https://docs.langchain.com/oss/python/integrations/vectorstores/qdrant)

**Chroma** is also viable, and its official site describes it as open-source infrastructure for vector, full-text, regex, and metadata search. [\[trychroma.com\]](https://www.trychroma.com/)

For your entry-level machine, **Qdrant local mode** is the cleaner starting point because it gives you:

*   no extra infrastructure burden
*   persistent on-disk option
*   easy migration later to a full server deployment if your workload grows [\[docs.langchain.com\]](https://docs.langchain.com/oss/python/integrations/vectorstores/qdrant)

### Layer 5 — UI / frontend

Use **CopilotKit** for the web front-end experience if your goal includes agentic UI.

Official CopilotKit docs describe it as the **frontend stack for agents and generative UI**, and the docs explicitly list:

*   **LangChain** integration
*   **MCP Apps**
*   **MCP (Agents<->Tools)** support for connecting MCP servers into React applications. [\[docs.copilotkit.ai\]](https://docs.copilotkit.ai/), [\[docs.copilotkit.ai\]](https://docs.copilotkit.ai/learn/connect-mcp-servers)

This makes CopilotKit a strong front-end layer **after** your backend runtime is stable.

***

# 4) The implementation stance you should adopt

## Core principle: “small brain, big tools, grounded answers”

Your local 3B model should do:

*   route intent
*   decide whether to search docs
*   decide whether to invoke MCP tools
*   summarize retrieved context

It should **not** try to internally memorize everything.

That is the only design that fits:

*   **3B-class weights**
*   **tight NPU context**
*   **entry-level system RAM / shared VRAM**
*   **your need for up-to-date and expandable capabilities** [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Project_Review_20260407_2244.md), [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/NPU_QUICKSTART.md), [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Intel_GPU_Optimization_Exec_Guide.md)

***

# 5) Recommended model routing policy

This part is **my implementation recommendation**, based on your files and the cited platform docs.

## Tier 1 — NPU fast orchestration model

Use `llama3.2:3b` as:

*   router
*   tool selector
*   RAG answer synthesizer
*   short interactive assistant

Why:

*   your project review records usable NPU speed for `llama3.2:3b` [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Project_Review_20260407_2244.md)
*   [NPU\_QUICKSTART.md](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/NPU_QUICKSTART.md?EntityRepresentationId=5fd3f910-ae0b-436a-af9b-e17fee133fd3) lists `llama-3.2-3b:latest` as a recommended model for the NPU-optimized engine. [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/NPU_QUICKSTART.md)

## Tier 2 — GPU reasoning model

Use a 7B-class model on the Intel GPU for:

*   longer reasoning
*   more complex synthesis
*   background indexing tasks
*   optional reranking or summarization jobs

Your own review recommends `deepseek-r1:7b` as a realistic GPU target and advises dropping 9B optimization for this machine. [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Project_Review_20260407_2244.md)

## Tier 3 — embeddings model

Use a small local embeddings model for RAG indexing and retrieval.

This is my recommendation, not a cited requirement:

*   choose a compact embeddings model to reduce RAM pressure
*   keep embeddings generation outside the NPU short-context chat path

***

# 6) Recommended development sequence

## Phase 1 — Stabilize the current runtime

Do **not** add agents before your runtime path is stable.

Your project review already identifies concrete defects:

*   wrong NPU flag for Arrow Lake
*   missing `port_warn` label
*   heredoc syntax issue in `.bat` flow [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Project_Review_20260407_2244.md)

And your GPU optimization guide says your scripts already aim to set optimal Intel flags such as `OLLAMA_NUM_GPU=999`. [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Intel_GPU_Optimization_Exec_Guide.md)

### Deliverable

A stable backend with:

*   deterministic startup
*   reliable model routing
*   clean CLI launch path
*   logging and benchmark capture

***

## Phase 2 — Add a retrieval core before full agents

Build a **RAG-first** enhancement before a multi-tool autonomous agent.

### Minimum RAG target

*   document ingestion
*   chunking
*   embeddings
*   local vector store
*   top-k retrieval
*   citations in answers

Qdrant’s official LangChain integration says you can run Qdrant in local mode with no server and persist on disk. That makes it ideal as your first retrieval layer. [\[docs.langchain.com\]](https://docs.langchain.com/oss/python/integrations/vectorstores/qdrant)

### Why this phase matters

It directly solves the problem you raised: “the model is not up-to-date in terms of knowledge or search capability.”

***

## Phase 3 — Add MCP for tool expansion

Once RAG works, then add MCP.

### First MCP server categories I recommend

This is my recommended prioritization:

1.  **filesystem/document tools**
2.  **search/retrieval tools**
3.  **system metrics / diagnostics tools**
4.  **database/query tools**
5.  **safe action tools** for controlled workflows

LangChain’s official MCP docs show multi-server access through `MultiServerMCPClient`, so this is a clean way to scale tool availability without rewriting your agent runtime. [\[docs.langchain.com\]](https://docs.langchain.com/oss/python/langchain/mcp)

***

## Phase 4 — Add web UI with CopilotKit

Only after the backend is stable.

CopilotKit’s docs explicitly position it as a frontend stack for agents, and they document both LangChain integration and MCP connectivity. [\[docs.copilotkit.ai\]](https://docs.copilotkit.ai/), [\[docs.copilotkit.ai\]](https://docs.copilotkit.ai/learn/connect-mcp-servers)

### Practical decision

*   keep CLI as the engineering console
*   use CopilotKit as the web UX layer
*   do not let the web UI become the source of business logic

This matches the fact that your existing [CLI\_QUICKSTART.md](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/CLI_QUICKSTART.md?EntityRepresentationId=51db8973-3637-4187-a0e7-d86b342ccc8e) already provides operational observability via `/stats`, `/switch`, and hardware-tier awareness. [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/CLI_QUICKSTART.md)

***

# 7) The non-negotiable design standards

## Standard 1 — Tool calls must be explicit, typed, and logged

Because local small models can hallucinate tool intent, every tool call should be:

*   schema-defined
*   validated
*   logged
*   replayable

This is especially important since you want MCP servers and future agentic workflows.

## Standard 2 — Retrieval must be cited

If an answer came from retrieved documents, your response pipeline should preserve source references.

This matters because RAG’s value is groundedness, not just better wording. Microsoft’s guidance explicitly frames RAG as improving grounded responses using enterprise content rather than relying only on model memory. [\[learn.microsoft.com\]](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/retrieval-augmented-generation)

## Standard 3 — Keep the NPU path lean

Because [NPU\_QUICKSTART.md](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/NPU_QUICKSTART.md?EntityRepresentationId=5fd3f910-ae0b-436a-af9b-e17fee133fd3) lists strict sequence and input limits, do not overload the NPU path with giant retrieval payloads. Retrieve, compress, then answer. [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/NPU_QUICKSTART.md)

## Standard 4 — Separate orchestration from serving

Your CLI guide shows the CLI consumes a serving layer on `11434`. Keep that separation:

*   server = inference runtime
*   agent runtime = orchestration and tools
*   UI = CLI/web frontend [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/CLI_QUICKSTART.md)

***

# 8) My recommended stack for **your** machine

This section is my recommendation, based on the cited constraints and platform docs.

## Backend

*   **Ollama-compatible serving layer** for model runtime
*   **LangChain / LangGraph** for orchestration
*   **MCP adapters** for tool discovery/execution
*   **Qdrant local mode** for vector retrieval

## Models

*   **Primary orchestration:** `llama3.2:3b`
*   **Secondary reasoning:** `deepseek-r1:7b` or another efficient 7B-class model
*   **Avoid interactive 9B optimization** on this machine unless you later accept degraded performance

Your own project review strongly supports this scope choice. [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Project_Review_20260407_2244.md)

## Frontend

*   keep the current **Rich CLI**
*   add **CopilotKit** for the web UI later

***

# 9) Reference implementation plan

## Sprint 1 — Runtime hardening

*   fix NPU flag logic
*   fix port-check crash path
*   fix batch heredoc issue
*   unify CLI startup with optimized backend launch  
    Supported by [Project\_Review\_20260407\_2244.md](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Project_Review_20260407_2244.md?EntityRepresentationId=ad95938d-5452-422e-988f-ac15e174e5b6). [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Project_Review_20260407_2244.md)

## Sprint 2 — Retrieval foundation

*   add ingestion pipeline
*   add chunking + embeddings
*   store in Qdrant local mode
*   implement retrieve → compress → answer loop  
    Supported by official Qdrant local-mode docs and Microsoft RAG guidance. [\[docs.langchain.com\]](https://docs.langchain.com/oss/python/integrations/vectorstores/qdrant), [\[learn.microsoft.com\]](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/retrieval-augmented-generation)

## Sprint 3 — MCP integration

*   implement MCP client layer through LangChain adapters
*   add 2–3 safe MCP servers first
*   enforce tool schemas and logs  
    Supported by official LangChain MCP docs. [\[docs.langchain.com\]](https://docs.langchain.com/oss/python/langchain/mcp)

## Sprint 4 — Agent behavior

*   add routing policy
*   add retry policy
*   add answer-citation policy
*   add model fallback policy  
    This is my recommendation, based on your hardware and runtime structure.

## Sprint 5 — Web UI

*   integrate CopilotKit runtime
*   connect to backend agent API
*   preserve CLI as admin/debug channel  
    Supported by CopilotKit docs. [\[docs.copilotkit.ai\]](https://docs.copilotkit.ai/), [\[docs.copilotkit.ai\]](https://docs.copilotkit.ai/learn/connect-mcp-servers)

***

# 10) Final directive

If you want this project to succeed on your current PC, your guiding doctrine should be:

> **Do not scale the model up. Scale the system out.**

On your hardware, success will come from:

*   **small local orchestration model**
*   **retrieval grounding**
*   **MCP tool access**
*   **clear routing between NPU / GPU tiers**
*   **tight observability through your CLI**
*   **optional CopilotKit UI once the backend is proven** [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/Project_Review_20260407_2244.md), [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/NPU_QUICKSTART.md), [\[gpgonline-...epoint.com\]](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/Documents/datapile/Microsoft%20Copilot%20Chat%20Files/CLI_QUICKSTART.md), [\[docs.langchain.com\]](https://docs.langchain.com/oss/python/langchain/mcp), [\[docs.copilotkit.ai\]](https://docs.copilotkit.ai/), [\[docs.copilotkit.ai\]](https://docs.copilotkit.ai/learn/connect-mcp-servers)

And one more useful note: your enterprise files already include internal agent-related material such as [Build Copilots in Copilot Studio - Microsoft AI Tour Workshop  .onepart](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/_layouts/15/Doc.aspx?action=edit\&mobileredirect=true\&wdorigin=Sharepoint\&DefaultItemOpen=1\&sourcedoc={3aafb833-1e41-48ce-889c-e112b72f448a}\&wd=target%28/GDoH%20ICT%20Applications%202024.one/%29\&wdpartid={f63cd9b8-382f-0389-0ec5-aafd786b260f}{1}\&wdsectionfileid={cc893275-bba6-4527-b40d-f3c6283c2288}\&EntityRepresentationId=ec43ce1d-48fd-4767-be4c-dafbc08a5ccb) and [Building Copilot Agents (Copilot Studio).onepart](https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/_layouts/15/Doc.aspx?action=edit\&mobileredirect=true\&wdorigin=Sharepoint\&DefaultItemOpen=1\&sourcedoc={3aafb833-1e41-48ce-889c-e112b72f448a}\&wd=target%28/GDoH%20ICT%20Applications%202024.one/%29\&wdpartid={676bc9b1-a624-0cfb-014c-7639e77de590}{1}\&wdsectionfileid={cc893275-bba6-4527-b40d-f3c6283c2288}\&EntityRepresentationId=72a2edbd-5b6d-43ad-85e2-b43798f23bb7), which may become relevant if you later want to align this local stack with a Microsoft tenant-facing agent strategy. \[15]\(<https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/_layouts/15/Doc.aspx?action=edit&mobileredirect=true&wdorigin=Sharepoint&DefaultItemOpen=1&sourcedoc={3aafb833-1e41-48ce-889c-e112b72f448a}&wd=target(/GDoH> ICT Applications 2024.one/)\&wdpartid={f63cd9b8-382f-0389-0ec5-aafd786b260f}{1}\&wdsectionfileid={cc893275-bba6-4527-b40d-f3c6283c2288})\[16]\(<https://gpgonline-my.sharepoint.com/personal/thabang_mposula_gauteng_gov_za/_layouts/15/Doc.aspx?action=edit&mobileredirect=true&wdorigin=Sharepoint&DefaultItemOpen=1&sourcedoc={3aafb833-1e41-48ce-889c-e112b72f448a}&wd=target(/GDoH> ICT Applications 2024.one/)\&wdpartid={676bc9b1-a624-0cfb-014c-7639e77de590}{1}\&wdsectionfileid={cc893275-bba6-4527-b40d-f3c6283c2288})

If you want, I can turn this into a **formal AGENTS.md-style implementation blueprint** tailored to your repo structure and Intel optimization pipeline.
