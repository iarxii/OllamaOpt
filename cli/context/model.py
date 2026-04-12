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
    system_chars: int = 500
    retrieved_docs_chars: int = 2000    # NPU path: keep small
    tool_output_chars: int = 1000
    memory_chars: int = 500
    history_chars: int = 1000
    total_hard_cap_chars: int = 3500    # strict ceiling for NPU 960-token limit


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
