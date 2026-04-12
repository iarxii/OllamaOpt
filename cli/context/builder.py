"""Context builder — assembles prompt segments deliberately with size control."""

from dataclasses import dataclass, field

from .compressor import Compressor
from .model import ContextPolicy, ContextSource


@dataclass
class AssembledContext:
    """The fully assembled, budget-capped context ready for prompt construction."""

    system_prompt: str = ""
    retrieved_context: str = ""
    tool_context: str = ""
    memory_context: str = ""
    history_context: str = ""
    sources_used: list = field(default_factory=list)
    total_chars: int = 0
    was_truncated: bool = False
    context_stats: dict = field(default_factory=dict)


class ContextBuilder:
    """Assembles prompt context from heterogeneous sources respecting a token/char budget.

    Priority order (highest → lowest):
        system → retrieved docs → tool results → memory → history → user query

    Each segment is capped at its per-segment budget.  After all segments are
    formatted the combined total is checked against `policy.budget.total_hard_cap_chars`
    and, if exceeded, excess characters are shed in reverse-priority order
    (history first, then memory, tools, retrieved docs).
    """

    def __init__(self, policy: ContextPolicy = None) -> None:
        self.policy: ContextPolicy = policy or ContextPolicy()
        self.compressor: Compressor = Compressor()
        self._system_prompt: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt that will appear first in every assembled context."""
        self._system_prompt = prompt

    def build(
        self,
        user_query: str,
        chat_history: list,
        retrieved_chunks: list,
        tool_results: list,
        memory_items: list,
    ) -> AssembledContext:
        """Assemble all context segments respecting per-segment and total hard-cap budgets.

        Parameters
        ----------
        user_query:
            The current user question (used only for stats; not embedded in the
            returned AssembledContext — attach it via assemble_prompt_string).
        chat_history:
            List of ``{"role": ..., "content": ...}`` message dicts.
        retrieved_chunks:
            Pre-retrieved document chunks as plain dicts (no RAG dependency).
        tool_results:
            Dicts with tool name and output from any tool calls in this turn.
        memory_items:
            Dicts or MemoryItem-like objects from session/episodic memory.

        Returns
        -------
        AssembledContext
            Fully assembled, budget-capped context with provenance metadata.
        """
        budget = self.policy.budget

        # 1. Format every segment within its individual budget
        system = self.compressor.truncate(self._system_prompt, budget.system_chars)
        retrieved = self._format_retrieved(retrieved_chunks, budget.retrieved_docs_chars)
        tools = self._format_tools(tool_results, budget.tool_output_chars)
        memory = self._format_memory(memory_items, budget.memory_chars)
        history = self._format_history(
            chat_history,
            self.policy.max_history_messages,
            budget.history_chars,
        )

        # 2. Enforce the total hard cap — trim in reverse-priority order
        was_truncated = False
        segments = [system, retrieved, tools, memory, history]
        total = sum(len(s) for s in segments)

        if total > budget.total_hard_cap_chars:
            was_truncated = True
            excess = total - budget.total_hard_cap_chars
            # Trim: history (4) → memory (3) → tools (2) → retrieved (1)
            for idx in (4, 3, 2, 1):
                if excess <= 0:
                    break
                trimable = len(segments[idx])
                if trimable == 0:
                    continue
                trim = min(trimable, excess)
                segments[idx] = segments[idx][: trimable - trim]
                excess -= trim

        system, retrieved, tools, memory, history = segments
        total_chars = sum(len(s) for s in segments)

        # 3. Build the sources_used provenance list
        sources_used: list = []
        if retrieved:
            for chunk in retrieved_chunks:
                entry: dict = {"source": ContextSource.RETRIEVED_DOCS.value}
                if isinstance(chunk, dict):
                    entry["title"] = chunk.get("title", "")
                    entry["path"] = chunk.get(
                        "source_path", chunk.get("path", "")
                    )
                sources_used.append(entry)

        if tools:
            for tool in tool_results:
                entry = {"source": ContextSource.TOOL_OUTPUT.value}
                if isinstance(tool, dict):
                    entry["tool_name"] = tool.get(
                        "tool_name", tool.get("name", "")
                    )
                sources_used.append(entry)

        if memory:
            for item in memory_items:
                entry = {"source": ContextSource.SESSION_MEMORY.value}
                if isinstance(item, dict):
                    entry["topic"] = item.get("topic", "")
                    entry["memory_id"] = item.get("memory_id", "")
                sources_used.append(entry)

        # 4. Build stats dict inline (avoids a redundant public call)
        stats: dict = {
            "system_chars": len(system),
            "retrieved_chars": len(retrieved),
            "tool_chars": len(tools),
            "memory_chars": len(memory),
            "history_chars": len(history),
            "total_chars": total_chars,
            "sources_count": len(sources_used),
            "was_truncated": was_truncated,
            "budget_used_pct": round(
                total_chars / max(budget.total_hard_cap_chars, 1) * 100, 1
            ),
        }

        return AssembledContext(
            system_prompt=system,
            retrieved_context=retrieved,
            tool_context=tools,
            memory_context=memory,
            history_context=history,
            sources_used=sources_used,
            total_chars=total_chars,
            was_truncated=was_truncated,
            context_stats=stats,
        )

    def assemble_prompt_string(
        self, assembled: AssembledContext, user_query: str
    ) -> str:
        """Concatenate all segments into a single prompt string.

        Priority order: system → retrieved docs → tool results → memory →
        history → user query.  Empty segments are omitted.
        """
        parts: list = []

        if assembled.system_prompt:
            parts.append(assembled.system_prompt)
        if assembled.retrieved_context:
            parts.append(assembled.retrieved_context)
        if assembled.tool_context:
            parts.append(assembled.tool_context)
        if assembled.memory_context:
            parts.append(assembled.memory_context)
        if assembled.history_context:
            parts.append(assembled.history_context)

        parts.append(f"User: {user_query}")
        return "\n\n".join(parts)

    def get_stats(self, assembled: AssembledContext) -> dict:
        """Return a dict summarising segment sizes, source count, and truncation status."""
        return {
            "system_chars": len(assembled.system_prompt),
            "retrieved_chars": len(assembled.retrieved_context),
            "tool_chars": len(assembled.tool_context),
            "memory_chars": len(assembled.memory_context),
            "history_chars": len(assembled.history_context),
            "total_chars": assembled.total_chars,
            "sources_count": len(assembled.sources_used),
            "was_truncated": assembled.was_truncated,
            "budget_used_pct": assembled.context_stats.get("budget_used_pct", 0.0),
        }

    # ------------------------------------------------------------------
    # Private segment formatters
    # ------------------------------------------------------------------

    def _format_retrieved(self, chunks: list, max_chars: int) -> str:
        """Format retrieved document chunks.

        Each chunk is rendered as::

            [Source: {title} | {source_path}]
            {content}

        Chunks are appended in order until the char budget is exhausted.
        """
        if not chunks:
            return ""
        parts: list = []
        used = 0
        for chunk in chunks:
            if isinstance(chunk, dict):
                title = chunk.get("title", "")
                path = chunk.get("source_path", chunk.get("path", ""))
                content = chunk.get("content", chunk.get("text", str(chunk)))
            else:
                title = ""
                path = ""
                content = str(chunk)

            header = f"[Source: {title} | {path}]"
            entry = f"{header}\n{content}\n"

            if used + len(entry) > max_chars:
                remaining = max_chars - used
                if remaining > len(header) + 5:
                    # Fit the header and as much content as possible
                    parts.append(entry[:remaining])
                break

            parts.append(entry)
            used += len(entry)

        return "\n".join(parts)

    def _format_tools(self, tools: list, max_chars: int) -> str:
        """Format tool call outputs.

        Each tool result is rendered as::

            [Tool: {tool_name}]
            {output}
        """
        if not tools:
            return ""
        parts: list = []
        used = 0
        for tool in tools:
            if isinstance(tool, dict):
                name = tool.get("tool_name", tool.get("name", "tool"))
                output = tool.get("output", tool.get("result", str(tool)))
            else:
                name = "tool"
                output = str(tool)

            header = f"[Tool: {name}]"
            entry = f"{header}\n{output}\n"

            if used + len(entry) > max_chars:
                remaining = max_chars - used
                if remaining > len(header) + 5:
                    parts.append(entry[:remaining])
                break

            parts.append(entry)
            used += len(entry)

        return "\n".join(parts)

    def _format_memory(self, items: list, max_chars: int) -> str:
        """Format session/episodic memory items.

        Each item is rendered as::

            [Memory: {topic}]
            {content}
        """
        if not items:
            return ""
        parts: list = []
        used = 0
        for item in items:
            if isinstance(item, dict):
                topic = item.get("topic", "")
                content = item.get("content", str(item))
            else:
                # Support MemoryItem dataclass instances via attribute access
                topic = getattr(item, "topic", "")
                content = getattr(item, "content", str(item))

            header = f"[Memory: {topic}]"
            entry = f"{header}\n{content}\n"

            if used + len(entry) > max_chars:
                remaining = max_chars - used
                if remaining > len(header) + 5:
                    parts.append(entry[:remaining])
                break

            parts.append(entry)
            used += len(entry)

        return "\n".join(parts)

    def _format_history(
        self, history: list, max_turns: int, max_chars: int
    ) -> str:
        """Format the tail of the conversation history.

        Keeps the last ``max_turns`` messages (each message counts as one item,
        so ``max_turns=6`` means up to 3 user/assistant pairs).  Each message is
        rendered as::

            User: {content}
            Assistant: {content}

        The whole block is additionally capped at ``max_chars``.
        """
        if not history:
            return ""

        # Slice to the last max_turns messages
        recent = history[-max_turns:] if len(history) > max_turns else history

        parts: list = []
        used = 0
        for msg in recent:
            if isinstance(msg, dict):
                raw_role = msg.get("role", "user")
                content = msg.get("content", "")
            else:
                raw_role = "user"
                content = str(msg)

            role_label = "Assistant" if raw_role.lower() in ("assistant", "bot", "system") else "User"
            line = f"{role_label}: {content}\n"

            if used + len(line) > max_chars:
                remaining = max_chars - used
                if remaining > 10:
                    parts.append(line[:remaining])
                break

            parts.append(line)
            used += len(line)

        return "".join(parts)
