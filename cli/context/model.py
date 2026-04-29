"""Context model — sources, priorities, and budget rules."""

from dataclasses import dataclass, field
from enum import Enum


class ContextSource(Enum):
    RETRIEVED_DOCS = "retrieved_docs"           # highest trust
    TOOL_OUTPUT = "tool_output"                 # high trust
    SESSION_MEMORY = "session_memory"           # medium trust
    CONVERSATION_HISTORY = "conversation_history"  # medium trust
    MODEL_KNOWLEDGE = "model_knowledge"         # lowest trust


class ContextPriority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


TRUST_ORDER = {
    ContextSource.RETRIEVED_DOCS: ContextPriority.HIGH,
    ContextSource.TOOL_OUTPUT: ContextPriority.HIGH,
    ContextSource.SESSION_MEMORY: ContextPriority.MEDIUM,
    ContextSource.CONVERSATION_HISTORY: ContextPriority.MEDIUM,
    ContextSource.MODEL_KNOWLEDGE: ContextPriority.LOW,
}


@dataclass
class ContextBudget:
    """Token/character budget for context segments."""
    system_chars: int = 400
    retrieved_docs_chars: int = 1500    # reduced to balance KV cache
    tool_output_chars: int = 800
    memory_chars: int = 400
    history_chars: int = 800
    total_hard_cap_chars: int = 3000    # strict balanced ceiling for local models


# ── Provider-Aware Budget Presets ────────────────────────────────────────────
# Local models (Ollama, llama.cpp) have limited KV cache (~3B params).
# Cloud providers (Groq, Gemini, OpenRouter) have 32K–2M context windows.

LOCAL_BUDGET = ContextBudget()  # defaults above — optimized for 3B KV cache

CLOUD_BUDGET = ContextBudget(
    system_chars=1200,
    retrieved_docs_chars=8000,
    tool_output_chars=4000,
    memory_chars=2000,
    history_chars=6000,
    total_hard_cap_chars=20000,
)

_CLOUD_PROVIDERS = {"groq", "openrouter", "gemini", "openai", "ollama_cloud"}

def get_budget_for_provider(provider: str) -> ContextBudget:
    """Select the appropriate context budget based on the active LLM provider."""
    if provider in _CLOUD_PROVIDERS:
        return CLOUD_BUDGET
    return LOCAL_BUDGET


@dataclass
class ContextPolicy:
    """Policy governing what may enter the prompt and how."""
    budget: ContextBudget = field(default_factory=ContextBudget)
    prefer_retrieved_over_model: bool = True
    prefer_tool_over_model: bool = True
    max_history_messages: int = 6
    enable_compression: bool = True
    enable_provenance: bool = True
    npu_strict_mode: bool = False   # if True, applies tighter budget for NPU path

    def apply_npu_mode(self):
        """Apply tighter budget for NPU 960-input-token path."""
        self.npu_strict_mode = True
        self.budget.retrieved_docs_chars = 800
        self.budget.tool_output_chars = 400
        self.budget.history_chars = 400
        self.budget.memory_chars = 200
        self.budget.total_hard_cap_chars = 1800

