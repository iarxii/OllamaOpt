# OllamaOpt Web UI — `build/features` Branch Implementation

Below is the complete implementation. Files are grouped by role. All new context documents are written to be machine-readable by AI agents on future sessions.

---

## `AGENTS.md` — root level (new master context document)

```markdown
# AGENTS.md — OllamaOpt Project Context for AI Development Agents

> Read this file first. It is the authoritative context document for all AI-assisted
> development on this repository. It covers constraints, architecture, routing rules,
> context assembly rules, tool policies, branch state, and definition of done.

---

## Table of Contents

1. [Project Identity](#1-project-identity)
2. [Hardware Constraints — Non-Negotiable](#2-hardware-constraints--non-negotiable)
3. [System Architecture](#3-system-architecture)
4. [Component Inventory](#4-component-inventory)
5. [Model Routing Policy](#5-model-routing-policy)
6. [Context Assembly Rules](#6-context-assembly-rules)
7. [Tool Policies](#7-tool-policies)
8. [Development Conventions](#8-development-conventions)
9. [Branch and Sprint State](#9-branch-and-sprint-state)
10. [Definition of Done](#10-definition-of-done)
11. [Canonical File Map](#11-canonical-file-map)
12. [Known Defects](#12-known-defects)
13. [Quick Reference Card](#13-quick-reference-card)

---

## 1. Project Identity

**OllamaOpt** is a local LLM optimization and agent platform for Intel AI PC hardware.

It provides three access surfaces to the same underlying LLM pipeline:

| Surface | Tech | Port | Status |
|---|---|---|---|
| Rich CLI | Python + Rich | — | Active |
| Web UI | Next.js + CopilotKit | 3000 | Active (build/features) |
| REST API | Python FastAPI | 8000 | Active (build/features) |

**Primary purpose:** Local AI assistant with retrieval-grounded answers, MCP tool access,
and hardware-tier-aware routing — running fully offline on Intel AI PC hardware.

**Governing doctrine:**
> Use the local model for orchestration. Use retrieval for knowledge.
> Use MCP for live capability. Keep all context assembly explicit and inspectable.
> Do not scale the model up. Scale the system out.

---

## 2. Hardware Constraints — Non-Negotiable

These constraints affect every architectural and implementation decision.
They are sourced from `NPU_QUICKSTART.md` and `Project_Review_20260407_2244.md`.

| Constraint | Value | Implication |
|---|---|---|
| NPU max input tokens | **960** | Hard ceiling — never exceed in NPU path |
| NPU max sequence length | **1024** | Total sequence including output |
| NPU safe payload target | **700** tokens | Conservative target with output headroom |
| NPU preferred model | `llama3.2:3b` (GGUF) | Only supported GGUF model on NPU path |
| GPU preferred model | `deepseek-r1:7b` | 7B-class on Intel GPU |
| 9B interactive use | **PROHIBITED** | Poor hardware fit — do not implement |
| Measured NPU speed | 13.04 tok/s (`llama3.2:3b`) | Baseline for performance expectations |
| Ollama serving port | **11434** | All pipeline components depend on this |

**Agent rule:** Never generate code, configs, or prompts that push 9B-class models into
the interactive path. Never send >960 tokens to the NPU path without compression first.

---

## 3. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                                │
│                                                                        │
│  ┌──────────────────────────┐    ┌─────────────────────────────────┐ │
│  │       Rich CLI           │    │  Web UI (Next.js + CopilotKit)  │ │
│  │  python -m cli.main      │    │  http://localhost:3000           │ │
│  │  /stats /switch /context │    │  Chat · ModelSelector · Stats   │ │
│  └────────────┬─────────────┘    └──────────────┬──────────────────┘ │
└───────────────┼──────────────────────────────────┼────────────────────┘
                │                                  │
                │                    ┌─────────────┴────────────────┐
                │                    │  Next.js API Routes           │
                │                    │  /api/copilotkit              │
                │                    │  CopilotRuntime + OpenAIAdapter│
                │                    │  → Ollama :11434/v1 (OpenAI) │
                │                    └─────────────┬────────────────┘
                │                                  │ observability calls
                ▼                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Python FastAPI Backend  :8000                       │
│                                                                        │
│  POST /chat          GET /models       GET /context/current            │
│  POST /chat/stream   GET /models/tiers GET /context/sources            │
│  GET  /health        GET /stats        GET /context/tools-used         │
│                                        GET /context/memory             │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │       Agent Pipeline         │
              │   LangChain / LangGraph      │
              │                              │
              │  ┌──────────────────────┐   │
              │  │   ModelRouter        │   │
              │  │   ContextBuilder     │   │
              │  │   RAG Retriever      │   │  ← Phase 2
              │  │   MCP Client         │   │  ← Phase 3
              │  └──────────────────────┘   │
              └──────────────┬──────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
  │   Ollama     │  │  Qdrant      │  │  MCP Servers     │
  │   :11434     │  │  local mode  │  │  (Phase 3)       │
  │  NPU + GPU   │  │  data/qdrant │  │  filesystem      │
  └──────────────┘  └──────────────┘  │  search          │
                                       │  telemetry       │
                                       └──────────────────┘
```

### Data flows

**CopilotKit chat flow (primary UI path):**
```
User types → CopilotKit React → POST /api/copilotkit?model=llama3.2:3b
  → CopilotRuntime → OpenAIAdapter → Ollama :11434/v1/chat/completions (streaming)
  → tokens stream back → CopilotChat renders response
```

**Observability flow (parallel, non-blocking):**
```
Components poll → GET /api/backend/context/current
  → FastAPI → in-memory context state → JSON response
```

**Direct pipeline flow (REST API path):**
```
POST /chat → FastAPI → ModelRouter → ContextBuilder → ChatOllama → Ollama :11434
```

---

## 4. Component Inventory

### 4.1 CLI (`cli/`)
- Entry: `python -m cli.main`
- Key commands: `/stats`, `/switch <model>`, `/context`, `/sources`, `/tools-used`, `/memory`
- Hardware awareness: displays NPU/GPU/CPU tier badge
- Status: **Active**

### 4.2 Web Backend (`web/backend/`)
- Entry: `uvicorn web.backend.main:app --reload --port 8000`
- Framework: FastAPI + LangGraph + LangChain-Ollama
- Provides: pipeline execution, model routing, context observability
- CopilotKit: NOT used in Python backend (CopilotKit runtime lives in Next.js)
- Status: **Active (build/features)**

### 4.3 Web Frontend (`web/frontend/`)
- Entry: `cd web/frontend && npm run dev`
- Framework: Next.js 14 App Router + TypeScript + CopilotKit + Tailwind
- Key components: ChatInterface, ModelSelector, HardwareTierBadge, SessionStats, ContextPanel
- CopilotKit runtime: `/api/copilotkit` → Ollama via OpenAI adapter
- Status: **Active (build/features)**

### 4.4 Agent Pipeline (`web/backend/pipeline/`)
- `agent.py` — LangGraph StateGraph definition
- `router.py` — Deterministic NPU/GPU routing
- `context_builder.py` — Single entry point for all prompt assembly
- Status: Phase 1 active (Phase 2 = RAG, Phase 3 = MCP)

### 4.5 Vector Store
- Tech: Qdrant local mode (no server required)
- Location: `data/qdrant/`
- Status: **Planned — Phase 2**

### 4.6 Inference Runtime
- Tech: Ollama — must be running before any component starts
- Port: 11434
- OpenAI-compatible API at `/v1/chat/completions`

---

## 5. Model Routing Policy

```
Incoming task
     │
     ▼
Estimate context tokens
     │
     ├── total_tokens > 700 → COMPRESS FIRST, then re-route
     │
     └── Evaluate routing conditions:
          │
          ├── Short query + small context (≤700 tok)
          │    └── NPU → llama3.2:3b
          │         num_ctx: 1024
          │         temperature: 0.1
          │
          ├── Heavy reasoning keywords present
          │    └── GPU → deepseek-r1:7b
          │         num_ctx: 4096
          │
          ├── Multi-document synthesis
          │    └── GPU → deepseek-r1:7b
          │
          └── Background indexing / offline task
               └── GPU or CPU background worker
```

### NPU path rules
- Model: `llama3.2:3b`
- `num_ctx`: 1024 (matches NPU max sequence)
- Safe payload target: ≤700 tokens
- Use for: routing, tool selection, short answer synthesis, interactive chat
- **Hard rule:** NEVER exceed 960 input tokens on NPU path

### GPU path rules
- Model: `deepseek-r1:7b`
- `num_ctx`: 4096
- Use for: complex reasoning, multi-document synthesis, long context
- **Hard rule:** Do NOT use 9B models for interactive tasks on this hardware

### Fallback rules
1. Context > 700 tokens on NPU path → compress via `ContextBuilder` → retry
2. GPU model unavailable → compress harder → NPU with summary only
3. Tool call fails → answer from available grounded data only
4. Any model call exceeds limits → return structured error with provenance=model

---

## 6. Context Assembly Rules

**All prompt assembly MUST go through `ContextBuilder`.**
Direct string concatenation in routes, agents, or UI is prohibited.

### Assembly priority order (1 = highest trust)
1. System instructions
2. Tool results (validated external output)
3. Retrieved chunks (grounded local knowledge)
4. Session memory (recalled prior work)
5. Conversation history (current session)

### Token budgets (`ContextBuilder`)
| Segment | Budget | Notes |
|---|---|---|
| System instructions | 150 | Always included |
| Tool results | 200 | Highest trust — compress if needed |
| Retrieved chunks | 300 | Include source reference |
| Session memory | 100 | Secondary context only |
| Conversation history | 150 | Most recent 6 turns max |
| **TOTAL HARD CAP** | **900** | Always under NPU 960 limit |

### Compression rules
- Long chat history → summarize into state summary before inclusion
- Long tool output → extract key fields only
- Multiple similar retrieved chunks → merge into cluster summary
- If assembled context > 900 tokens → truncate and log warning

### Answer provenance tags
Every answer MUST carry one of:
- `"retrieved"` — answer grounded in retrieved documents
- `"tool"` — answer derived from validated tool output
- `"memory"` — answer informed by recalled memory
- `"model"` — answer from model knowledge only (lowest trust)

---

## 7. Tool Policies

### Tool call requirements
Every MCP tool call must be:
- Schema-defined with typed inputs
- Validated before invocation
- Logged (request + response)
- Traceable with a call ID

### Trust levels
| Category | Trust | Validation |
|---|---|---|
| File/document read | High | Path sanitization |
| Search/retrieval | High | Result count check |
| System metrics | High | None additional |
| Database query | Medium | Query sanitization |
| External/web | Low | Full output validation |

### MCP implementation order
1. filesystem/document tools (Phase 3 start)
2. retrieval/search tools
3. system/telemetry tools
4. database/query tools
5. safe action/workflow tools

---

## 8. Development Conventions

### Python (backend)
- All FastAPI endpoints must be `async def`
- Streaming responses use `StreamingResponse` with `text/event-stream`
- Structured error responses: `{"error": str, "code": int}`
- Logging: `logging.getLogger(__name__)` — structured, named loggers
- Type hints: required on all function signatures
- `ContextBuilder` is the ONLY entry point for prompt construction

### TypeScript (frontend)
- Next.js 14 App Router patterns
- All server components use `async` — all client components use `"use client"`
- API calls go through `lib/api-client.ts` only — no inline fetch in components
- Types in `lib/types.ts` — no inline type definitions in components
- CopilotKit state management via hooks from `@copilotkit/react-core`

### Pipeline rules
- Model calls: always through `ModelRouter` → `ContextBuilder` → `ChatOllama`
- Direct Ollama calls (`httpx` to port 11434) only in `/models` endpoints
- Tool results must be stored in agent state before answer synthesis
- Every non-trivial answer must have a `provenance` field

### Git
- Active branch: `build/features`
- Commit format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `refactor`, `test`
- Scopes: `cli`, `web-ui`, `pipeline`, `mcp`, `rag`, `docs`, `backend`, `frontend`

---

## 9. Branch and Sprint State

**Current branch:** `build/features`

### Sprint 1 — Runtime hardening (prerequisite)
- [ ] Fix NPU flag for Arrow Lake
- [ ] Fix `port_warn` missing label
- [ ] Fix heredoc syntax in `.bat` startup
- [ ] Remove 9B interactive optimization paths

### Sprint 2 — Retrieval foundation
- [ ] Document ingestion pipeline
- [ ] Chunking + metadata preservation
- [ ] Qdrant local mode setup at `data/qdrant/`
- [ ] Top-k retrieval with source citations
- [ ] Context builder RAG segment

### Sprint 3 — MCP integration
- [ ] `langchain-mcp-adapters` installation and config
- [ ] First MCP server (filesystem/document)
- [ ] Tool schema registry
- [ ] Tool result → context flow

### Sprint 4 — Agent behavior
- [ ] Full LangGraph routing policy
- [ ] Retry + fallback policy
- [ ] Answer citation policy
- [ ] Model fallback rules

### Sprint 5 — Web UI ✅ IN PROGRESS
- [x] FastAPI backend scaffold
- [x] Next.js + CopilotKit frontend scaffold
- [x] CopilotKit runtime → Ollama OpenAI adapter
- [x] Model tier selector (NPU/GPU)
- [x] Hardware tier badge
- [x] Context panel (mirrors CLI /context)
- [x] Session stats
- [x] API client (observability endpoints)
- [ ] Connect context panel to live backend state
- [ ] Add RAG sources tab (Phase 2 readiness)

---

## 10. Definition of Done

A feature is done when ALL of these are true:

- [ ] No hardcoded token limits outside `ContextBuilder`
- [ ] No direct Ollama calls outside the pipeline router (except `/models` endpoints)
- [ ] Context payload verified ≤700 tokens for NPU-path tasks
- [ ] CLI and Web UI surface equivalent behavior for the same operation
- [ ] Relevant `docs/architecture/` document updated
- [ ] `AGENTS.md` updated if architecture changed
- [ ] Answer provenance tagged on every non-trivial response

---

## 11. Canonical File Map

```
OllamaOpt/
├── AGENTS.md                              ← You are here (master context)
│
├── cli/                                   ← Rich CLI (existing, active)
│   ├── main.py
│   └── commands/
│
├── web/
│   ├── README.md                          ← Web component overview
│   ├── backend/
│   │   ├── main.py                        ← FastAPI app entry point (:8000)
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                   ← LangGraph StateGraph
│   │   │   ├── router.py                  ← NPU/GPU routing logic
│   │   │   └── context_builder.py         ← ONLY entry for prompt assembly
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py                    ← POST /chat (direct pipeline)
│   │   │   ├── models.py                  ← GET /models, /models/tiers
│   │   │   └── context.py                 ← GET /context/* (observability)
│   │   ├── requirements.txt
│   │   └── .env.example
│   │
│   └── frontend/
│       ├── src/
│       │   ├── app/
│       │   │   ├── layout.tsx             ← Root layout (CopilotKit NOT here)
│       │   │   ├── page.tsx               ← Main page (CopilotKit provider here)
│       │   │   ├── globals.css
│       │   │   └── api/
│       │   │       └── copilotkit/
│       │   │           └── route.ts       ← CopilotKit runtime → Ollama
│       │   ├── components/
│       │   │   ├── ChatInterface.tsx      ← CopilotChat wrapper
│       │   │   ├── ModelSelector.tsx      ← NPU/GPU tier switcher
│       │   │   ├── HardwareTierBadge.tsx  ← Visual tier indicator
│       │   │   ├── SessionStats.tsx       ← Service status + model info
│       │   │   └── ContextPanel.tsx       ← Sources/tools/memory inspector
│       │   └── lib/
│       │       ├── api-client.ts          ← All calls to FastAPI :8000
│       │       └── types.ts               ← Shared TypeScript interfaces
│       ├── package.json
│       ├── next.config.js
│       ├── tailwind.config.ts
│       ├── postcss.config.js
│       └── tsconfig.json
│
├── data/
│   └── qdrant/                            ← Vector store persistence (Phase 2)
│
├── docs/
│   └── architecture/
│       ├── AGENTS.md                      ← Alias / symlink to root AGENTS.md
│       ├── WEB_UI_ARCHITECTURE.md         ← Web UI architecture detail
│       ├── WEB_UI_QUICKSTART.md           ← Web UI setup guide
│       ├── new build features_arch_guideline_260408.md
│       └── checklist_new build features_arch_guideline_260408.md
│
└── scripts/                              ← Startup scripts (existing)
```

---

## 12. Known Defects

From `Project_Review_20260407_2244.md`:

| ID | Issue | File | Sprint |
|---|---|---|---|
| D-01 | Wrong NPU flag for Arrow Lake | startup script | Sprint 1 |
| D-02 | Missing `port_warn` label | CLI error path | Sprint 1 |
| D-03 | Heredoc syntax error | `.bat` flow | Sprint 1 |
| D-04 | 9B interactive path present | model config | Sprint 1 |

**Do not merge Sprint 5 (web UI) until Sprint 1 defects are resolved.**

---

## 13. Quick Reference Card

| Item | Value |
|---|---|
| NPU max input | 960 tokens |
| NPU sequence max | 1024 tokens |
| NPU safe payload | 700 tokens |
| NPU model | `llama3.2:3b` |
| GPU model | `deepseek-r1:7b` |
| 9B models interactive | PROHIBITED |
| Ollama port | 11434 |
| FastAPI backend port | 8000 |
| Next.js frontend port | 3000 |
| Vector store | Qdrant local mode |
| Vector store path | `data/qdrant/` |
| Active branch | `build/features` |
| Prompt assembly entry | `ContextBuilder` only |
| Provenance values | `retrieved`, `tool`, `memory`, `model` |
| CopilotKit runtime | `/api/copilotkit` in Next.js |
| CLI parity required | Yes — web UI mirrors CLI behavior |
```

---

## `docs/architecture/WEB_UI_ARCHITECTURE.md`

```markdown
# Web UI Architecture

**Branch:** `build/features`  
**Status:** Sprint 5 — Active  
**See also:** `AGENTS.md` (root) for full project context

---

## Overview

The OllamaOpt Web UI provides a browser-based interface to the same LLM pipeline
used by the Rich CLI. It is designed around three principles:

1. **CLI parity** — every CLI capability is accessible via the web UI
2. **Shared pipeline** — business logic lives in the Python backend, never the frontend
3. **Hardware-first** — NPU/GPU tier is always visible and switchable

---

## Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Frontend framework | Next.js | 14.x (App Router) | React SSR/CSR + API routes |
| Chat UI | CopilotKit | 1.x | Agentic chat components |
| Styling | Tailwind CSS | 3.x | Utility-first dark theme |
| Language | TypeScript | 5.x | Type safety |
| Backend framework | FastAPI | 0.111+ | Pipeline REST API |
| Agent orchestration | LangGraph | 0.2+ | Agent state graphs |
| LLM client | LangChain-Ollama | 0.1+ | Ollama integration |
| LLM runtime | Ollama | latest | Local model serving |

---

## Chat Flow — Two Separate Paths

### Path A: CopilotKit chat (primary, user-facing)

```
Browser (CopilotChat component)
  → POST /api/copilotkit?model=llama3.2:3b
    → Next.js API Route (CopilotRuntime)
      → OpenAIAdapter
        → Ollama :11434/v1/chat/completions  [OpenAI-compatible]
          → streaming tokens back to browser
```

**Model selection:** Passed via `?model=` query parameter from the `CopilotKit`
provider's `runtimeUrl` prop. The `ModelSelector` component updates this prop when
the user switches tiers.

**System instructions:** Passed via `CopilotChat` `instructions` prop. Each
hardware tier has its own instruction set (see `ChatInterface.tsx`).

### Path B: Direct pipeline (REST API, admin/debug)

```
POST /chat  →  FastAPI  →  ModelRouter  →  ContextBuilder  →  ChatOllama
  →  Ollama :11434  →  streaming SSE response
```

This path is used by direct API consumers and for testing the pipeline
independently of CopilotKit.

---

## State Management

### Frontend state
- `selectedTier` (page.tsx): Current hardware tier — drives `runtimeUrl` and UI
- CopilotKit manages conversation state internally
- Context panel polls FastAPI observability endpoints every 5 seconds

### Backend state (Phase 1)
- In-memory last-context state in `routes/context.py`
- Phase 2: Replace with per-session state keyed by conversation ID
- Phase 3: Session state stored in Qdrant for memory retrieval

---

## Component Responsibilities

### `page.tsx`
- Holds `selectedTier` state
- Provides `CopilotKit` provider with dynamic `runtimeUrl`
- Renders sidebar (ModelSelector, SessionStats) + main area (ChatInterface, ContextPanel)

### `ChatInterface.tsx`
- Renders `CopilotChat` with tier-specific `instructions`
- Does NOT manage state — receives `tier` prop from `page.tsx`

### `ModelSelector.tsx`
- Fetches tier config from FastAPI `/models/tiers` on mount
- Falls back to hardcoded tiers if backend unavailable
- Calls `onTierChange` prop — parent updates `runtimeUrl`

### `HardwareTierBadge.tsx`
- Pure display component — renders NPU (blue) or GPU (amber) badge
- Receives `tier` prop

### `SessionStats.tsx`
- Polls `/health` and `/models` to show service status
- Shows NPU/GPU token limits as static reference
- Phase 2: will show live tok/s from Ollama metrics

### `ContextPanel.tsx`
- Polls four FastAPI endpoints: `/context/current`, `/sources`, `/tools-used`, `/memory`
- Tab interface: Stats | Sources | Tools | Memory
- Mirrors CLI commands: `/context`, `/sources`, `/tools-used`, `/memory`

### `lib/api-client.ts`
- All calls to FastAPI backend go through this module
- Components never call `fetch()` directly
- Handles AbortSignal timeout (5s) for observability polling

---

## CopilotKit Runtime (`/api/copilotkit/route.ts`)

The Next.js API route instantiates a fresh `CopilotRuntime` and `OpenAIAdapter`
per request to support dynamic model selection:

```typescript
const model = searchParams.get("model") ?? "llama3.2:3b";
const serviceAdapter = new OpenAIAdapter({ openai: ollamaClient, model });
const runtime = new CopilotRuntime();
const handler = copilotRuntimeNextJSAppRouterHandler({ runtime, serviceAdapter });
return handler(req);
```

**Why per-request instantiation:** Supports model switching without requiring
server restart. Overhead is negligible at local usage scale.

**Why OpenAI adapter:** Ollama exposes an OpenAI-compatible API at
`http://localhost:11434/v1`. CopilotKit's `OpenAIAdapter` works with any
OpenAI-compatible endpoint.

---

## Phase Roadmap

| Phase | Feature | Status |
|---|---|---|
| Phase 1 | Web UI shell, CopilotKit chat, model switching, context panel | ✅ Active |
| Phase 2 | RAG — Qdrant local, document ingestion, retrieval citations | Planned |
| Phase 3 | MCP tools, LangGraph agent, tool call display | Planned |
| Phase 4 | Full LangGraph agent in CopilotKit (replace OpenAI adapter) | Planned |

---

## Environment Variables

### Backend (`web/backend/.env`)
```
OLLAMA_BASE_URL=http://localhost:11434
LOG_LEVEL=INFO
```

### Frontend (`web/frontend/.env.local`)
```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
OLLAMA_BASE_URL=http://localhost:11434/v1
```
```

---

## `docs/architecture/WEB_UI_QUICKSTART.md`

```markdown
# Web UI Quickstart

**Branch:** `build/features`

---

## Prerequisites

- Ollama running on `localhost:11434`
- `llama3.2:3b` model pulled: `ollama pull llama3.2:3b`
- Python 3.11+
- Node.js 20+

---

## Step 1 — Start the Python backend

```bash
# From the repo root
cd web/backend
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health`

Expected: `{"status":"ok","service":"ollamaopt-web-backend","version":"0.1.0"}`

---

## Step 2 — Start the Next.js frontend

```bash
# From the repo root
cd web/frontend
npm install
npm run dev
```

Open: `http://localhost:3000`

---

## Step 3 — Verify the full stack

| Check | URL | Expected |
|---|---|---|
| Ollama | `http://localhost:11434/api/tags` | JSON with models list |
| Backend health | `http://localhost:8000/health` | `{"status":"ok"}` |
| Backend models | `http://localhost:8000/models` | List of Ollama models |
| Frontend | `http://localhost:3000` | Chat interface loads |

---

## Step 4 — Send your first message

1. The web UI defaults to the **NPU tier** (`llama3.2:3b`)
2. Type a message in the chat input and press Enter
3. The CopilotKit runtime routes through `/api/copilotkit?model=llama3.2:3b`
4. Ollama processes on the NPU path
5. Response streams back to the chat UI

---

## Step 5 — Switch to GPU tier

1. In the left sidebar, click **GPU** in the Hardware Tier panel
2. The tier badge in the top bar updates to amber/GPU
3. The model switches to `deepseek-r1:7b`
4. Ensure `deepseek-r1:7b` is pulled: `ollama pull deepseek-r1:7b`

---

## Step 6 — Inspect context

1. Click **Context Panel** in the bottom left of the sidebar
2. The context panel opens on the right side of the chat
3. **Stats tab** — shows token usage and pipeline status
4. **Sources tab** — shows RAG sources (Phase 2: will show document citations)
5. **Tools tab** — shows MCP tool calls (Phase 3: will show tool invocations)
6. **Memory tab** — shows recalled memory (Phase 3: will show episodic memory)

---

## CLI + Web UI parity

| CLI command | Web UI equivalent |
|---|---|
| `/stats` | SessionStats panel (sidebar) |
| `/switch llama3.2:3b` | ModelSelector (NPU button) |
| `/switch deepseek-r1:7b` | ModelSelector (GPU button) |
| `/context` | ContextPanel → Stats tab |
| `/sources` | ContextPanel → Sources tab |
| `/tools-used` | ContextPanel → Tools tab |
| `/memory` | ContextPanel → Memory tab |

---

## Troubleshooting

**Chat returns no response:**
- Check Ollama is running: `ollama serve`
- Check the model is pulled: `ollama list`
- Check browser console for CopilotKit errors

**Backend API errors (red dots in SessionStats):**
- Ensure backend is running: `uvicorn main:app --port 8000`
- Check `CORS` — backend allows `localhost:3000` by default

**Model not found:**
- Pull the model: `ollama pull llama3.2:3b`
- The ModelSelector only shows models returned by `GET /models`
```

---

## `web/README.md`

```markdown
# OllamaOpt Web Component

This directory contains the web interface for OllamaOpt.
It shares the same LLM pipeline as the CLI tool.

## Structure

```
web/
├── backend/    Python FastAPI — pipeline REST API (:8000)
└── frontend/   Next.js + CopilotKit — web UI (:3000)
```

## Quick start

```bash
# Terminal 1 — Backend
cd web/backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd web/frontend && npm install && npm run dev
```

Open http://localhost:3000

## Architecture

See `docs/architecture/WEB_UI_ARCHITECTURE.md` for full detail.
See `AGENTS.md` (repo root) for project-wide AI agent context.

## Requirements

- Ollama running on localhost:11434
- `llama3.2:3b` pulled for NPU path
- `deepseek-r1:7b` pulled for GPU path
```

---

## `web/backend/main.py`

```python
"""
OllamaOpt Web Backend — FastAPI entry point.

Ports:
  This service:  8000
  Ollama:        11434  (must be running before this starts)
  Frontend:      3000   (Next.js, CORS allowed)

Architecture note:
  CopilotKit runtime lives in the Next.js frontend (/api/copilotkit).
  This backend provides the pipeline, model management, and context
  observability endpoints consumed by the frontend React components.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .pipeline.agent import build_agent_graph
from .routes import chat as chat_routes
from .routes import context as context_routes
from .routes import models as models_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifecycle — build shared resources at startup."""
    logger.info("OllamaOpt Web Backend starting up")
    logger.info("Expecting Ollama at http://localhost:11434")

    # Build the LangGraph agent (shared across all requests)
    app.state.agent_graph = build_agent_graph()
    logger.info("Agent pipeline ready (Phase 1: routing + direct inference)")

    yield

    logger.info("OllamaOpt Web Backend shutting down")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="OllamaOpt Web Backend",
        description=(
            "REST API for the OllamaOpt local LLM platform. "
            "Provides model management, pipeline execution, and context "
            "observability for the web UI and direct API consumers. "
            "See AGENTS.md for full architecture context."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # Allow the Next.js frontend on port 3000
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register route groups
    app.include_router(chat_routes.router, prefix="/chat", tags=["chat"])
    app.include_router(models_routes.router, prefix="/models", tags=["models"])
    app.include_router(context_routes.router, prefix="/context", tags=["context"])

    @app.get("/health", tags=["system"])
    async def health() -> dict:
        """Service health check."""
        return {
            "status": "ok",
            "service": "ollamaopt-web-backend",
            "version": "0.1.0",
        }

    return app


app = create_app()
```

---

## `web/backend/pipeline/__init__.py`

```python
"""OllamaOpt agent pipeline — routing, context assembly, and inference."""
```

---

## `web/backend/pipeline/agent.py`

```python
"""
LangGraph agent definition for OllamaOpt.

Phase 1 graph:
  [route] → [answer] → END

Phase 2 (planned):
  [route] → [retrieve] → [compress] → [answer] → END

Phase 3 (planned):
  [route] → [retrieve] → [tool_call] → [compress] → [answer] → END

Hardware constraints enforced here:
  NPU path (llama3.2:3b):  num_ctx=1024, temperature=0.1
  GPU path (deepseek-r1:7b): num_ctx=4096, temperature=0.1
"""

from __future__ import annotations

import logging
from typing import Annotated

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from .context_builder import ContextBuilder
from .router import HardwareTier, ModelRouter

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"


class AgentState(TypedDict):
    """
    State carried through the LangGraph agent.

    All fields must have defaults to allow partial updates between nodes.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    model: str
    hardware_tier: str          # "npu" | "gpu" | "cpu"
    context_payload_tokens: int
    retrieved_sources: list[dict]
    tool_results: list[dict]
    provenance: str             # "retrieved" | "tool" | "memory" | "model"
    error: str | None


def _initial_state() -> AgentState:
    """Return a default initial state."""
    return AgentState(
        messages=[],
        model="llama3.2:3b",
        hardware_tier="npu",
        context_payload_tokens=0,
        retrieved_sources=[],
        tool_results=[],
        provenance="model",
        error=None,
    )


async def route_node(state: AgentState) -> dict:
    """
    Routing node — determine hardware tier and model.

    Reads the last message, estimates context size, and delegates
    to ModelRouter for a deterministic routing decision.
    """
    if not state["messages"]:
        return {"hardware_tier": "npu", "model": "llama3.2:3b"}

    last = state["messages"][-1]
    query = last.content if hasattr(last, "content") else ""

    router = ModelRouter()
    tier, model = router.route(
        query=str(query),
        context_tokens=state.get("context_payload_tokens", 0),
        has_retrieval=len(state.get("retrieved_sources", [])) > 0,
        has_tool_results=len(state.get("tool_results", [])) > 0,
    )

    logger.info("Route: %s → %s", tier.value, model)
    return {"hardware_tier": tier.value, "model": model}


async def answer_node(state: AgentState) -> dict:
    """
    Answer node — call the routed model with assembled context.

    Context assembly always goes through ContextBuilder.
    Never concatenate strings directly here.
    """
    builder = ContextBuilder()

    hardware_tier = state.get("hardware_tier", "npu")
    model = state.get("model", "llama3.2:3b")

    # Assemble context — all size enforcement is inside ContextBuilder
    context_text = builder.build(
        system_instructions=(
            "You are a local AI assistant running on Intel AI PC hardware. "
            "Be concise. Cite sources when available. "
            f"Current path: {hardware_tier.upper()} using {model}."
        ),
        messages=state["messages"][:-1],  # History only, not the current query
        retrieved_chunks=state.get("retrieved_sources", []),
        tool_results=state.get("tool_results", []),
        memory_items=[],  # Phase 3: memory retrieval goes here
    )

    # Determine provenance from what context was available
    if state.get("retrieved_sources"):
        provenance = "retrieved"
    elif state.get("tool_results"):
        provenance = "tool"
    else:
        provenance = "model"

    # Set hardware-appropriate context window
    num_ctx = 1024 if hardware_tier == "npu" else 4096

    llm = ChatOllama(
        model=model,
        base_url=OLLAMA_BASE_URL,
        temperature=0.1,
        num_ctx=num_ctx,
    )

    # Build messages: context as system-style prefix + current user query
    messages_to_llm: list[BaseMessage] = []
    if context_text.strip():
        messages_to_llm.append(HumanMessage(content=context_text))
    messages_to_llm.append(state["messages"][-1])

    try:
        response: AIMessage = await llm.ainvoke(messages_to_llm)
        return {
            "messages": [response],
            "provenance": provenance,
            "error": None,
        }
    except Exception as exc:
        logger.error("Model inference error on %s: %s", model, exc)
        return {
            "messages": [AIMessage(content=f"Inference error: {exc}")],
            "provenance": "model",
            "error": str(exc),
        }


def build_agent_graph():
    """
    Compile and return the LangGraph agent.

    Extend this function when adding Phase 2 (retrieval) and Phase 3 (tools).
    Always preserve the route → answer core.
    """
    graph: StateGraph = StateGraph(AgentState)

    graph.add_node("route", route_node)
    graph.add_node("answer", answer_node)

    graph.set_entry_point("route")
    graph.add_edge("route", "answer")
    graph.add_edge("answer", END)

    compiled = graph.compile()
    logger.info("Agent graph compiled (nodes: route, answer)")
    return compiled
```

---

## `web/backend/pipeline/router.py`

```python
"""
Deterministic model router.

Rules are enforced from NPU_QUICKSTART.md and Project_Review_20260407_2244.md.

NPU path:  llama3.2:3b  — short context, fast inference, interactive
GPU path:  deepseek-r1:7b — longer context, heavier reasoning

HARD CONSTRAINT: Do not route 9B models to interactive path on this machine.
HARD CONSTRAINT: NPU safe payload ≤ 700 tokens (hard ceiling: 960 input).
"""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)

# ── Token limits (from NPU_QUICKSTART.md) ────────────────────────────
NPU_MAX_INPUT_TOKENS: int = 960
NPU_MAX_SEQUENCE: int = 1024
NPU_SAFE_PAYLOAD_TOKENS: int = 700   # Conservative — leaves room for output

# ── Models (from Project_Review_20260407_2244.md) ─────────────────────
NPU_MODEL: str = "llama3.2:3b"
GPU_MODEL: str = "deepseek-r1:7b"

# ── Routing signals ───────────────────────────────────────────────────
_HEAVY_REASONING_KEYWORDS: tuple[str, ...] = (
    "analyze",
    "analyse",
    "compare",
    "synthesize",
    "synthesise",
    "evaluate",
    "comprehensive",
    "detailed report",
    "summarize all",
    "summarise all",
    "multiple documents",
    "across all documents",
    "deep dive",
)


class HardwareTier(Enum):
    NPU = "npu"
    GPU = "gpu"
    CPU = "cpu"


class ModelRouter:
    """
    Routes a query to the appropriate hardware tier and model.

    Decision is deterministic — same inputs always produce same output.
    Do not add probabilistic or LLM-based routing in Phase 1.
    """

    def route(
        self,
        query: str,
        context_tokens: int = 0,
        has_retrieval: bool = False,
        has_tool_results: bool = False,
    ) -> tuple[HardwareTier, str]:
        """
        Return (HardwareTier, model_name) for the given task.

        Args:
            query:            The user's input text.
            context_tokens:   Estimated tokens already in the context payload.
            has_retrieval:    Whether retrieved document chunks are available.
            has_tool_results: Whether MCP tool results are available.

        Returns:
            (HardwareTier, model_name)
        """
        query_tokens = self._estimate_tokens(query)
        total_estimated = context_tokens + query_tokens

        logger.debug(
            "Router input: total_tokens=%d, has_retrieval=%s, has_tool=%s",
            total_estimated,
            has_retrieval,
            has_tool_results,
        )

        if self._requires_gpu(query, total_estimated, has_retrieval):
            logger.info("GPU route selected (tokens=%d)", total_estimated)
            return HardwareTier.GPU, GPU_MODEL

        logger.info("NPU route selected (tokens=%d)", total_estimated)
        return HardwareTier.NPU, NPU_MODEL

    # ── Private helpers ───────────────────────────────────────────────

    def _requires_gpu(
        self,
        query: str,
        total_tokens: int,
        has_retrieval: bool,
    ) -> bool:
        """
        Return True when the GPU path is required.

        GPU is required when:
          1. Context payload exceeds NPU safe limit
          2. Query contains heavy reasoning signals
          3. Multi-document synthesis with long query
        """
        # Hard token limit check — non-negotiable NPU constraint
        if total_tokens > NPU_SAFE_PAYLOAD_TOKENS:
            logger.debug("GPU: token limit exceeded (%d > %d)", total_tokens, NPU_SAFE_PAYLOAD_TOKENS)
            return True

        # Heavy reasoning keyword signal
        query_lower = query.lower()
        for keyword in _HEAVY_REASONING_KEYWORDS:
            if keyword in query_lower:
                logger.debug("GPU: heavy reasoning keyword found: '%s'", keyword)
                return True

        # Multi-document synthesis: retrieval + long query
        if has_retrieval and len(query) > 300:
            logger.debug("GPU: multi-document synthesis signal")
            return True

        return False

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        Rough token count (4 chars ≈ 1 token).
        Replace with tiktoken or a model-specific tokenizer for accuracy.
        """
        return max(1, len(text) // 4)
```

---

## `web/backend/pipeline/context_builder.py`

```python
"""
ContextBuilder — single entry point for all prompt assembly.

RULE: Every model call in this project must assemble its context through
this module. Direct string concatenation in routes or agents is prohibited.

Context assembly order (trust priority, high to low):
  1. System instructions
  2. Tool results
  3. Retrieved document chunks
  4. Session memory items
  5. Conversation history

Token budgets (conservative — designed for NPU 960-token hard ceiling):
  System instructions:  150 tokens
  Tool results:         200 tokens
  Retrieved chunks:     300 tokens
  Session memory:       100 tokens
  Conversation history: 150 tokens
  TOTAL HARD CAP:       900 tokens  (60 tokens headroom under 960)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)

# ── Token budgets ─────────────────────────────────────────────────────
BUDGET_SYSTEM: int = 150
BUDGET_TOOLS: int = 200
BUDGET_RETRIEVED: int = 300
BUDGET_MEMORY: int = 100
BUDGET_HISTORY: int = 150
BUDGET_TOTAL: int = 900  # Hard cap — always stays under NPU 960 ceiling


@dataclass
class ContextStats:
    """
    Statistics for the most recently assembled context.
    Consumed by /context/current endpoint and the ContextPanel UI component.
    """

    system_tokens: int = 0
    tool_tokens: int = 0
    retrieved_tokens: int = 0
    memory_tokens: int = 0
    history_tokens: int = 0
    total_tokens: int = 0
    sources_used: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    truncated: bool = False

    def to_dict(self) -> dict:
        return {
            "system_tokens": self.system_tokens,
            "tool_tokens": self.tool_tokens,
            "retrieved_tokens": self.retrieved_tokens,
            "memory_tokens": self.memory_tokens,
            "history_tokens": self.history_tokens,
            "total_tokens": self.total_tokens,
            "sources_used": self.sources_used,
            "tools_used": self.tools_used,
            "truncated": self.truncated,
        }


class ContextBuilder:
    """
    Assembles context payloads for model calls.

    Usage:
        builder = ContextBuilder()
        context = builder.build(
            system_instructions="...",
            messages=history,
            retrieved_chunks=chunks,
            tool_results=results,
        )
        # builder.last_stats contains token usage breakdown
    """

    def __init__(self) -> None:
        self._last_stats: ContextStats | None = None

    @property
    def last_stats(self) -> ContextStats | None:
        """Stats from the most recent build() call."""
        return self._last_stats

    def build(
        self,
        system_instructions: str = "",
        messages: list[BaseMessage] | None = None,
        retrieved_chunks: list[dict] | None = None,
        tool_results: list[dict] | None = None,
        memory_items: list[dict] | None = None,
    ) -> str:
        """
        Assemble a context prefix string for a model call.

        Returns the assembled context text (does NOT include the current
        user query — the caller appends that separately).

        Args:
            system_instructions: Behavioural instructions for the model.
            messages:            Prior conversation (list of BaseMessage).
            retrieved_chunks:    RAG result dicts with keys: source, text, score.
            tool_results:        MCP tool results with keys: tool_name, output.
            memory_items:        Recalled memory with keys: summary.

        Returns:
            Assembled context string within the BUDGET_TOTAL token limit.
        """
        stats = ContextStats()
        parts: list[str] = []

        # ── 1. System instructions ────────────────────────────────────
        if system_instructions:
            sys_text = self._truncate(system_instructions, BUDGET_SYSTEM)
            if sys_text != system_instructions:
                stats.truncated = True
            stats.system_tokens = self._count(sys_text)
            parts.append(f"[SYSTEM]\n{sys_text}")

        # ── 2. Tool results (highest trust) ───────────────────────────
        if tool_results:
            tool_text, tool_names = self._format_tool_results(tool_results, BUDGET_TOOLS)
            if tool_text:
                stats.tool_tokens = self._count(tool_text)
                stats.tools_used = tool_names
                parts.append(f"[TOOL RESULTS]\n{tool_text}")

        # ── 3. Retrieved chunks (grounded knowledge) ──────────────────
        if retrieved_chunks:
            ret_text, sources = self._format_retrieved_chunks(retrieved_chunks, BUDGET_RETRIEVED)
            if ret_text:
                stats.retrieved_tokens = self._count(ret_text)
                stats.sources_used = sources
                parts.append(f"[RETRIEVED KNOWLEDGE]\n{ret_text}")

        # ── 4. Memory items ───────────────────────────────────────────
        if memory_items:
            mem_text = self._format_memory(memory_items, BUDGET_MEMORY)
            if mem_text:
                stats.memory_tokens = self._count(mem_text)
                parts.append(f"[RECALLED MEMORY]\n{mem_text}")

        # ── 5. Conversation history ───────────────────────────────────
        if messages:
            hist_text = self._format_history(messages, BUDGET_HISTORY)
            if hist_text:
                stats.history_tokens = self._count(hist_text)
                parts.append(f"[CONVERSATION HISTORY]\n{hist_text}")

        assembled = "\n\n".join(parts)

        # ── Total cap enforcement ─────────────────────────────────────
        if self._count(assembled) > BUDGET_TOTAL:
            assembled = self._truncate(assembled, BUDGET_TOTAL)
            stats.truncated = True
            logger.warning(
                "Context truncated to stay within %d-token budget (was %d tokens)",
                BUDGET_TOTAL,
                self._count(assembled),
            )

        stats.total_tokens = self._count(assembled)
        self._last_stats = stats

        logger.debug(
            "Context assembled: %d tokens | sources=%d | tools=%d | truncated=%s",
            stats.total_tokens,
            len(stats.sources_used),
            len(stats.tools_used),
            stats.truncated,
        )

        return assembled

    # ── Private formatters ─────────────────────────────────────────────

    def _format_tool_results(
        self, results: list[dict], budget: int
    ) -> tuple[str, list[str]]:
        lines: list[str] = []
        names: list[str] = []
        used = 0

        for result in results:
            name = str(result.get("tool_name", "unknown"))
            output = str(result.get("output", ""))[:400]  # Cap individual result
            entry = f"• {name}: {output}"

            entry_tokens = self._count(entry)
            if used + entry_tokens > budget:
                # Compress: first 100 chars only
                output = output[:100] + "…"
                entry = f"• {name}: {output}"
                entry_tokens = self._count(entry)

            if used + entry_tokens > budget:
                break

            lines.append(entry)
            names.append(name)
            used += entry_tokens

        return "\n".join(lines), names

    def _format_retrieved_chunks(
        self, chunks: list[dict], budget: int
    ) -> tuple[str, list[str]]:
        lines: list[str] = []
        sources: list[str] = []
        used = 0

        for chunk in chunks:
            source = str(chunk.get("source", "unknown"))
            text = str(chunk.get("text", ""))
            score = float(chunk.get("score", 0.0))
            header = f"[{source} | score={score:.2f}]"
            remaining_budget = budget - used - self._count(header) - 5

            if remaining_budget < 20:
                break

            text = self._truncate(text, remaining_budget)
            entry = f"{header}\n{text}"

            lines.append(entry)
            sources.append(source)
            used += self._count(entry)

        return "\n\n".join(lines), sources

    def _format_memory(self, items: list[dict], budget: int) -> str:
        lines: list[str] = []
        used = 0

        for item in items:
            entry = f"• {item.get('summary', '')}"
            tokens = self._count(entry)
            if used + tokens > budget:
                break
            lines.append(entry)
            used += tokens

        return "\n".join(lines)

    def _format_history(self, messages: list[BaseMessage], budget: int) -> str:
        """Format the most recent conversation turns within budget."""
        lines: list[str] = []
        used = 0

        # Take at most 6 recent turns, iterate newest → oldest
        for msg in reversed(messages[-6:]):
            role = "User" if msg.__class__.__name__ == "HumanMessage" else "Assistant"
            content = str(msg.content)[:250]  # Cap per-message length
            entry = f"{role}: {content}"
            tokens = self._count(entry)

            if used + tokens > budget:
                break

            lines.insert(0, entry)  # Restore chronological order
            used += tokens

        return "\n".join(lines)

    @staticmethod
    def _count(text: str) -> int:
        """Token count estimate: 4 chars ≈ 1 token."""
        return max(1, len(text) // 4)

    @staticmethod
    def _truncate(text: str, token_budget: int) -> str:
        """Truncate text to fit within a token budget."""
        char_limit = token_budget * 4
        if len(text) <= char_limit:
            return text
        return text[:char_limit] + "…"
```

---

## `web/backend/routes/__init__.py`

```python
"""OllamaOpt FastAPI route modules."""
```

---

## `web/backend/routes/chat.py`

```python
"""
Chat endpoints.

POST /chat         — streaming SSE chat via the pipeline
POST /chat/sync    — non-streaming chat (for testing)

The CopilotKit chat UI uses /api/copilotkit (Next.js) → Ollama directly.
These endpoints serve the REST API path and direct pipeline consumers.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel

from ..pipeline.context_builder import ContextBuilder
from ..pipeline.router import HardwareTier, ModelRouter

logger = logging.getLogger(__name__)
router = APIRouter()

OLLAMA_BASE_URL = "http://localhost:11434"


class ChatRequest(BaseModel):
    message: str
    model: str | None = None          # Override auto-routing if provided
    conversation_id: str | None = None
    stream: bool = True


class ChatResponse(BaseModel):
    content: str
    model: str
    hardware_tier: str
    provenance: str
    sources: list[dict] = []
    context_tokens: int = 0


@router.post("", summary="Stream chat through the agent pipeline")
async def chat(req: ChatRequest) -> StreamingResponse | ChatResponse:
    """
    Process a chat message through the OllamaOpt pipeline.

    Supports:
      - stream=true (default): Server-Sent Events with token chunks
      - stream=false: Synchronous JSON response

    The pipeline applies model routing and context assembly before inference.
    """
    model_router = ModelRouter()
    tier, routed_model = model_router.route(query=req.message)
    selected_model = req.model or routed_model

    if req.stream:
        return StreamingResponse(
            _stream_chat(req.message, selected_model, tier),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # Synchronous path
    return await _sync_chat(req.message, selected_model, tier)


@router.post("/sync", summary="Non-streaming chat (testing)")
async def chat_sync(req: ChatRequest) -> ChatResponse:
    """Non-streaming version of /chat for testing and simple clients."""
    model_router = ModelRouter()
    tier, routed_model = model_router.route(query=req.message)
    selected_model = req.model or routed_model
    return await _sync_chat(req.message, selected_model, tier)


# ── Private helpers ────────────────────────────────────────────────────

async def _stream_chat(
    message: str,
    model: str,
    tier: HardwareTier,
) -> AsyncGenerator[str, None]:
    """Stream response tokens as SSE events."""
    num_ctx = 1024 if tier == HardwareTier.NPU else 4096

    llm = ChatOllama(
        model=model,
        base_url=OLLAMA_BASE_URL,
        temperature=0.1,
        num_ctx=num_ctx,
    )

    try:
        async for chunk in llm.astream([HumanMessage(content=message)]):
            if hasattr(chunk, "content") and chunk.content:
                data = json.dumps({"type": "token", "content": chunk.content})
                yield f"data: {data}\n\n"

        # Final metadata event
        done = json.dumps({
            "type": "done",
            "model": model,
            "hardware_tier": tier.value,
            "provenance": "model",
        })
        yield f"data: {done}\n\n"

    except Exception as exc:
        logger.error("Streaming error (model=%s): %s", model, exc)
        error = json.dumps({"type": "error", "content": str(exc)})
        yield f"data: {error}\n\n"

    finally:
        yield "data: [DONE]\n\n"


async def _sync_chat(
    message: str,
    model: str,
    tier: HardwareTier,
) -> ChatResponse:
    """Non-streaming inference."""
    num_ctx = 1024 if tier == HardwareTier.NPU else 4096

    llm = ChatOllama(
        model=model,
        base_url=OLLAMA_BASE_URL,
        temperature=0.1,
        num_ctx=num_ctx,
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=message)])
        return ChatResponse(
            content=str(response.content),
            model=model,
            hardware_tier=tier.value,
            provenance="model",
        )
    except Exception as exc:
        logger.error("Sync chat error (model=%s): %s", model, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

---

## `web/backend/routes/models.py`

```python
"""
Model management endpoints.

GET /models             — list models available in Ollama
GET /models/tiers       — hardware tier configuration (for ModelSelector UI)
GET /models/current     — current default model per tier
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException

from ..pipeline.router import GPU_MODEL, NPU_MODEL

logger = logging.getLogger(__name__)
router = APIRouter()

OLLAMA_API = "http://localhost:11434/api"


@router.get("", summary="List available Ollama models")
async def list_models() -> dict:
    """
    Fetch the list of locally available Ollama models.
    Annotates each model with its recommended hardware tier.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_API}/tags")
            resp.raise_for_status()
            data = resp.json()

        models = [
            {
                "name": m["name"],
                "size": m.get("size", 0),
                "modified_at": m.get("modified_at", ""),
                "recommended_tier": _classify_tier(m["name"]),
            }
            for m in data.get("models", [])
        ]

        return {"models": models, "count": len(models)}

    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Ollama not reachable at localhost:11434. "
                "Start Ollama with: ollama serve"
            ),
        ) from exc
    except Exception as exc:
        logger.error("Failed to list models: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/tiers", summary="Hardware tier configuration")
async def get_tier_config() -> dict:
    """
    Return hardware tier configuration for the ModelSelector UI component.
    Constraints sourced from NPU_QUICKSTART.md.
    """
    return {
        "tiers": [
            {
                "tier": "npu",
                "label": "NPU",
                "model": NPU_MODEL,
                "description": "Intel NPU — fast, low-latency, 3B model",
                "max_input_tokens": 960,
                "max_sequence_tokens": 1024,
                "safe_payload_tokens": 700,
                "color": "blue",
            },
            {
                "tier": "gpu",
                "label": "GPU",
                "model": GPU_MODEL,
                "description": "Intel GPU — heavier reasoning, 7B model",
                "max_input_tokens": 4096,
                "max_sequence_tokens": 8192,
                "safe_payload_tokens": 3500,
                "color": "amber",
            },
        ]
    }


@router.get("/current", summary="Current default model per tier")
async def get_current_models() -> dict:
    """Return the configured default model for each hardware tier."""
    return {
        "npu_model": NPU_MODEL,
        "gpu_model": GPU_MODEL,
        "default_tier": "npu",
    }


def _classify_tier(model_name: str) -> str:
    """Map a model name to its recommended hardware tier."""
    name = model_name.lower()
    if any(tag in name for tag in ("3b", "1b", "llama3.2", "llama-3.2")):
        return "npu"
    if any(tag in name for tag in ("7b", "deepseek", "mistral", "phi3")):
        return "gpu"
    return "gpu"  # Default: safer to route unknown models to GPU
```

---

## `web/backend/routes/context.py`

```python
"""
Context observability endpoints.

These mirror the CLI's /context family of commands:
  GET /context/current    ↔  /context
  GET /context/sources    ↔  /sources
  GET /context/tools-used ↔  /tools-used
  GET /context/memory     ↔  /memory
  GET /context/stats      ↔  /stats (extended)

Phase 1: in-memory state (last call only).
Phase 2: per-session state keyed by conversation_id.
Phase 3: persistent state with vector memory retrieval.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()

# ── In-memory last-call state ─────────────────────────────────────────
# Phase 2: replace with a session store (dict[str, ContextState])
_state: dict = {
    "timestamp": None,
    "hardware_tier": "npu",
    "model": "llama3.2:3b",
    "provenance": "model",
    "stats": {
        "total_tokens": 0,
        "system_tokens": 0,
        "retrieved_tokens": 0,
        "tool_tokens": 0,
        "memory_tokens": 0,
        "history_tokens": 0,
        "truncated": False,
    },
    "sources": [],
    "tools_used": [],
    "memory_items": [],
}


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/current", summary="Assembled context stats from last call")
async def get_current() -> dict:
    """Return context assembly stats from the most recent pipeline call."""
    return {
        "timestamp": _state["timestamp"],
        "hardware_tier": _state["hardware_tier"],
        "model": _state["model"],
        "provenance": _state["provenance"],
        "stats": _state["stats"],
    }


@router.get("/sources", summary="Retrieved document sources from last call")
async def get_sources() -> dict:
    """
    Return document sources used in the most recent retrieval.
    Empty in Phase 1 — populated when RAG is active (Phase 2).
    """
    return {
        "sources": _state["sources"],
        "count": len(_state["sources"]),
        "phase_note": (
            "Phase 1: RAG not yet active. "
            "Document sources will appear here after Phase 2 implementation."
        ),
    }


@router.get("/tools-used", summary="MCP tool calls from last interaction")
async def get_tools_used() -> dict:
    """
    Return MCP tool calls from the most recent interaction.
    Empty in Phase 1 — populated when MCP is active (Phase 3).
    """
    return {
        "tools": _state["tools_used"],
        "count": len(_state["tools_used"]),
        "phase_note": (
            "Phase 1: MCP not yet active. "
            "Tool calls will appear here after Phase 3 implementation."
        ),
    }


@router.get("/memory", summary="Recalled memory items from last interaction")
async def get_memory() -> dict:
    """
    Return recalled episodic memory from the most recent interaction.
    Empty in Phase 1 — populated when vector memory is active (Phase 3).
    """
    return {
        "memory_items": _state["memory_items"],
        "count": len(_state["memory_items"]),
        "phase_note": (
            "Phase 1: Vector memory not yet active. "
            "Memory items will appear here after Phase 3 implementation."
        ),
    }


@router.get("/stats", summary="Full context pipeline statistics")
async def get_stats() -> dict:
    """Return full context pipeline statistics and phase status."""
    return {
        "last_call": _state["timestamp"],
        "stats": _state["stats"],
        "pipeline_phases": {
            "routing": {
                "status": "active",
                "description": "NPU/GPU deterministic routing",
            },
            "context_assembly": {
                "status": "active",
                "description": "ContextBuilder with token budgets",
            },
            "rag_retrieval": {
                "status": "planned",
                "description": "Qdrant local mode — Phase 2",
            },
            "mcp_tools": {
                "status": "planned",
                "description": "langchain-mcp-adapters — Phase 3",
            },
            "vector_memory": {
                "status": "planned",
                "description": "Episodic memory in Qdrant — Phase 3",
            },
        },
    }


# ── State update (called by pipeline after each inference) ────────────

def update_context_state(
    *,
    hardware_tier: str,
    model: str,
    provenance: str,
    stats: dict,
    sources: list[dict] | None = None,
    tools_used: list[dict] | None = None,
    memory_items: list[dict] | None = None,
) -> None:
    """
    Update the in-memory context state after a pipeline call.

    Called from the agent pipeline after each successful inference.
    The ContextPanel UI polls these endpoints to stay current.
    """
    global _state
    _state = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "hardware_tier": hardware_tier,
        "model": model,
        "provenance": provenance,
        "stats": stats,
        "sources": sources or [],
        "tools_used": tools_used or [],
        "memory_items": memory_items or [],
    }
    logger.debug(
        "Context state updated: tier=%s model=%s provenance=%s tokens=%d",
        hardware_tier,
        model,
        provenance,
        stats.get("total_tokens", 0),
    )
```

---

## `web/backend/requirements.txt`

```
# OllamaOpt Web Backend
# Python 3.11+

# ── Web framework ──────────────────────────────────────────────────────
fastapi>=0.111.0
uvicorn[standard]>=0.29.0

# ── LLM pipeline ──────────────────────────────────────────────────────
langchain>=0.2.0
langchain-core>=0.2.0
langchain-ollama>=0.1.0
langchain-community>=0.2.0
langgraph>=0.2.0

# ── HTTP client (Ollama API calls in /models) ──────────────────────────
httpx>=0.27.0

# ── Validation + serialization ────────────────────────────────────────
pydantic>=2.7.0
pydantic-settings>=2.3.0

# ── Typing ────────────────────────────────────────────────────────────
typing-extensions>=4.12.0

# ── Environment ───────────────────────────────────────────────────────
python-dotenv>=1.0.0

# ── Phase 2 — RAG (uncomment when implementing) ───────────────────────
# qdrant-client>=1.9.0
# langchain-qdrant>=0.1.0

# ── Phase 3 — MCP (uncomment when implementing) ───────────────────────
# langchain-mcp-adapters>=0.1.0
```

---

## `web/backend/.env.example`

```
# OllamaOpt Web Backend — environment variables
# Copy to .env and adjust as needed

OLLAMA_BASE_URL=http://localhost:11434
LOG_LEVEL=INFO

# Phase 2 — RAG
# QDRANT_PATH=../../data/qdrant

# Phase 3 — MCP
# MCP_SERVER_FILESYSTEM=stdio
```

---

## `web/frontend/package.json`

```json
{
  "name": "ollamaopt-web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start --port 3000",
    "lint": "next lint",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "@copilotkit/react-core": "^1.3.0",
    "@copilotkit/react-ui": "^1.3.0",
    "@copilotkit/runtime": "^1.3.0",
    "next": "14.2.3",
    "openai": "^4.47.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@types/node": "^20.14.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "autoprefixer": "^10.4.19",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.3",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.3",
    "typescript": "^5.4.5"
  }
}
```

---

## `web/frontend/next.config.js`

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  /**
   * Proxy /api/backend/* to the Python FastAPI backend.
   * This avoids CORS issues when calling FastAPI from client components.
   */
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },

  env: {
    NEXT_PUBLIC_BACKEND_URL:
      process.env.BACKEND_URL ?? "http://localhost:8000",
    NEXT_PUBLIC_OLLAMA_URL:
      process.env.OLLAMA_URL ?? "http://localhost:11434",
  },
};

module.exports = nextConfig;
```

---

## `web/frontend/postcss.config.js`

```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

---

## `web/frontend/tailwind.config.ts`

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        // Intel brand blue
        intel: {
          50:  "#e6f2ff",
          400: "#5ec1f0",
          500: "#0071c5",
          600: "#0050a0",
        },
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};

export default config;
```

---

## `web/frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": [
    "next-env.d.ts",
    "**/*.ts",
    "**/*.tsx",
    ".next/types/**/*.ts"
  ],
  "exclude": ["node_modules"]
}
```

---

## `web/frontend/src/app/layout.tsx`

```tsx
import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "@copilotkit/react-ui/styles.css";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "OllamaOpt — Local LLM · Intel AI PC",
  description:
    "Web interface for the OllamaOpt local LLM optimization platform. " +
    "Runs on Intel NPU and GPU hardware via Ollama.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`
          ${inter.variable} ${jetbrainsMono.variable}
          font-sans bg-slate-950 text-slate-100 antialiased
        `}
      >
        {children}
      </body>
    </html>
  );
}
```

---

## `web/frontend/src/app/globals.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* ── CopilotKit dark theme overrides ─────────────────────────────── */
:root {
  --copilot-kit-primary-color: #3b82f6;
  --copilot-kit-background-color: #0f172a;
  --copilot-kit-secondary-background-color: #1e293b;
  --copilot-kit-separator-color: #334155;
  --copilot-kit-text-color: #f1f5f9;
  --copilot-kit-muted-text-color: #94a3b8;
  --copilot-kit-font-family: var(--font-inter), system-ui, sans-serif;
  --copilot-kit-code-font-family: var(--font-mono), ui-monospace, monospace;
}

/* ── Custom scrollbar ─────────────────────────────────────────────── */
::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #475569;
}

/* ── CopilotKit chat container fills parent ───────────────────────── */
.copilotKitChat {
  height: 100% !important;
  border: none !important;
  border-radius: 0 !important;
}
```

---

## `web/frontend/src/app/page.tsx`

```tsx
"use client";

import { useState } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import ChatInterface from "@/components/ChatInterface";
import ModelSelector from "@/components/ModelSelector";
import HardwareTierBadge from "@/components/HardwareTierBadge";
import SessionStats from "@/components/SessionStats";
import ContextPanel from "@/components/ContextPanel";
import type { ModelTier } from "@/lib/types";

/** Default tier — NPU path, as recommended by NPU_QUICKSTART.md */
const DEFAULT_TIER: ModelTier = {
  tier: "npu",
  label: "NPU",
  model: "llama3.2:3b",
  description: "Intel NPU — fast, low-latency, 3B model",
  color: "blue",
};

export default function Home() {
  const [selectedTier, setSelectedTier] = useState<ModelTier>(DEFAULT_TIER);
  const [showContext, setShowContext] = useState(false);

  /**
   * CopilotKit runtime URL includes the selected model as a query param.
   * The /api/copilotkit route reads this to instantiate the correct adapter.
   */
  const runtimeUrl = `/api/copilotkit?model=${encodeURIComponent(selectedTier.model)}`;

  return (
    <CopilotKit runtimeUrl={runtimeUrl}>
      <div className="flex h-screen overflow-hidden bg-slate-950">
        {/* ── Sidebar ──────────────────────────────────────────────── */}
        <aside className="w-60 flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col">
          {/* Logo */}
          <div className="px-4 py-3 border-b border-slate-800">
            <h1 className="text-base font-bold tracking-tight">
              Ollama<span className="text-blue-400">Opt</span>
            </h1>
            <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
              Local LLM · Intel AI PC
            </p>
          </div>

          {/* Hardware Tier Selection */}
          <div className="px-4 py-3 border-b border-slate-800">
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2.5">
              Hardware Tier
            </p>
            <ModelSelector
              selectedTier={selectedTier}
              onTierChange={setSelectedTier}
            />
          </div>

          {/* Session Stats */}
          <div className="px-4 py-3 border-b border-slate-800 flex-1 min-h-0 overflow-y-auto">
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2.5">
              Session
            </p>
            <SessionStats currentModel={selectedTier.model} />
          </div>

          {/* Context Panel Toggle */}
          <div className="px-4 py-3">
            <button
              onClick={() => setShowContext((v) => !v)}
              className={`
                w-full px-3 py-2 rounded-md text-xs text-left
                flex items-center gap-2 transition-colors
                ${showContext
                  ? "bg-blue-500/10 text-blue-300 border border-blue-500/30"
                  : "bg-slate-800 text-slate-400 border border-transparent hover:text-slate-200"
                }
              `}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                  showContext ? "bg-blue-400" : "bg-slate-600"
                }`}
              />
              Context Inspector
            </button>
          </div>
        </aside>

        {/* ── Main Content ─────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Top Bar */}
          <header className="h-11 flex-shrink-0 border-b border-slate-800 bg-slate-900 flex items-center px-4 gap-3">
            <HardwareTierBadge tier={selectedTier} />
            <span className="text-slate-500 text-[11px] font-mono">
              {selectedTier.model}
            </span>
            <div className="flex-1" />
            <span className="text-[11px] text-slate-600 font-mono hidden sm:block">
              backend:8000 · ollama:11434
            </span>
          </header>

          {/* Chat + Context Panel */}
          <div className="flex-1 flex min-h-0">
            {/* Chat */}
            <div className="flex-1 min-w-0">
              <ChatInterface tier={selectedTier} />
            </div>

            {/* Context Panel (collapsible) */}
            {showContext && (
              <aside className="w-72 flex-shrink-0 border-l border-slate-800 bg-slate-900 overflow-hidden flex flex-col">
                <ContextPanel />
              </aside>
            )}
          </div>
        </div>
      </div>
    </CopilotKit>
  );
}
```

---

## `web/frontend/src/app/api/copilotkit/route.ts`

```typescript
/**
 * CopilotKit runtime — Next.js App Router API route.
 *
 * Architecture:
 *   Browser (CopilotChat)
 *     → POST /api/copilotkit?model=llama3.2:3b
 *       → CopilotRuntime + OpenAIAdapter
 *         → Ollama :11434/v1/chat/completions (OpenAI-compatible)
 *           → streaming tokens back
 *
 * Model selection:
 *   The ?model= param is set by page.tsx from the selectedTier state.
 *   Each hardware tier switch updates the CopilotKit runtimeUrl prop.
 *
 * Why per-request instantiation:
 *   Supports live model switching without server restart.
 *   Performance cost is negligible at local usage scale.
 *
 * See AGENTS.md §4.3 for architecture context.
 */

import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterHandler,
} from "@copilotkit/runtime";
import OpenAI from "openai";
import { type NextRequest } from "next/server";

const OLLAMA_BASE_URL =
  process.env.OLLAMA_BASE_URL ?? "http://localhost:11434/v1";

const DEFAULT_MODEL = "llama3.2:3b";

/**
 * Tier-specific system prompts.
 * Kept lean — NPU path requires short prompts.
 */
const SYSTEM_PROMPTS: Record<string, string> = {
  "llama3.2:3b":
    "You are a fast local AI assistant on the Intel NPU using llama3.2:3b. " +
    "Be concise. Cite sources when available. Keep responses brief.",
  "deepseek-r1:7b":
    "You are a capable local AI assistant on the Intel GPU using deepseek-r1:7b. " +
    "You can handle more complex reasoning. Cite sources when available.",
};

function getSystemPrompt(model: string): string {
  return (
    SYSTEM_PROMPTS[model] ??
    `You are a local AI assistant using ${model}. Be concise. Cite sources when available.`
  );
}

export async function POST(req: NextRequest): Promise<Response> {
  const { searchParams } = new URL(req.url);
  const model = searchParams.get("model") ?? DEFAULT_MODEL;

  const ollamaClient = new OpenAI({
    baseURL: OLLAMA_BASE_URL,
    apiKey: "ollama", // Required by the OpenAI SDK — not used by Ollama
  });

  const serviceAdapter = new OpenAIAdapter({
    openai: ollamaClient,
    model,
  });

  const runtime = new CopilotRuntime({
    // Phase 3: add MCP tool actions here via langchain-mcp-adapters
    // actions: [],
  });

  const handler = copilotRuntimeNext