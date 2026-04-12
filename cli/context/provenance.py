"""Answer provenance and trust tracking."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AnswerLabel(Enum):
    RETRIEVED_FROM_DOCS = "retrieved_from_docs"
    DERIVED_FROM_TOOL = "derived_from_tool"
    FROM_SESSION_MEMORY = "from_session_memory"
    MODEL_GENERATED = "model_generated"


@dataclass
class ProvenanceRecord:
    """Tracks the origin and trustworthiness of a generated answer."""
    label: AnswerLabel
    sources: list = field(default_factory=list)
    tool_names: list = field(default_factory=list)
    memory_ids: list = field(default_factory=list)
    chunk_ids: list = field(default_factory=list)
    grounded: bool = False
    timestamp: str = ""


class ProvenanceTracker:
    """Records and formats provenance for each assistant response."""

    def __init__(self):
        self._history: list = []

    def create_record(self, assembled_context) -> ProvenanceRecord:
        """Inspect an AssembledContext to determine the appropriate provenance label.

        Priority order:
          1. RETRIEVED_FROM_DOCS  — retrieved_context is non-empty
          2. DERIVED_FROM_TOOL    — tool_context is non-empty
          3. FROM_SESSION_MEMORY  — memory_context is non-empty
          4. MODEL_GENERATED      — nothing external was injected
        """
        if assembled_context.retrieved_context:
            label = AnswerLabel.RETRIEVED_FROM_DOCS
        elif assembled_context.tool_context:
            label = AnswerLabel.DERIVED_FROM_TOOL
        elif assembled_context.memory_context:
            label = AnswerLabel.FROM_SESSION_MEMORY
        else:
            label = AnswerLabel.MODEL_GENERATED

        grounded = label != AnswerLabel.MODEL_GENERATED
        sources = list(assembled_context.sources_used)

        tool_names = [
            s.get("tool_name", "")
            for s in sources
            if s.get("source") == "tool_output" and s.get("tool_name")
        ]
        chunk_ids = [
            str(s.get("path", s.get("title", "")))
            for s in sources
            if s.get("source") == "retrieved_docs"
        ]

        return ProvenanceRecord(
            label=label,
            sources=sources,
            tool_names=tool_names,
            memory_ids=[],
            chunk_ids=chunk_ids,
            grounded=grounded,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def format_label(self, record: ProvenanceRecord) -> str:
        """Return a short Rich-markup string describing the answer's provenance."""
        if record.grounded:
            label_map = {
                AnswerLabel.RETRIEVED_FROM_DOCS: "Retrieved from documents",
                AnswerLabel.DERIVED_FROM_TOOL: "Derived from tool output",
                AnswerLabel.FROM_SESSION_MEMORY: "From session memory",
            }
            desc = label_map.get(record.label, "Grounded")
            return f"[green]✓ Grounded[/green] · {desc}"
        return "[yellow]⚠ Model knowledge[/yellow]"

    def track(self, record: ProvenanceRecord) -> None:
        """Append a record to the internal history list."""
        self._history.append(record)

    def get_history(self) -> list:
        """Return a copy of all tracked ProvenanceRecords."""
        return list(self._history)
