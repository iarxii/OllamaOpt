"""Context compressor — truncation and summary helpers."""


class Compressor:
    """Handles text truncation and token/character estimation for context segments."""

    def truncate(self, text: str, max_chars: int, suffix: str = "... [truncated]") -> str:
        """Hard truncate text to max_chars, appending suffix if truncated."""
        if not text or len(text) <= max_chars:
            return text
        cut = max_chars - len(suffix)
        if cut <= 0:
            return suffix[:max_chars]
        return text[:cut] + suffix

    def truncate_history(self, messages: list, max_chars: int) -> list:
        """Keep the most recent messages until the char budget is exhausted.

        Iterates from the end of the message list and accumulates messages
        until the char budget runs out, then returns them in original order.
        """
        if not messages:
            return []
        result = []
        used = 0
        for msg in reversed(messages):
            if isinstance(msg, dict):
                content = msg.get("content", "")
            else:
                content = str(msg)
            # +20 accounts for role prefix overhead ("User: " / "Assistant: " + newline)
            cost = len(content) + 20
            if used + cost > max_chars:
                break
            result.insert(0, msg)
            used += cost
        return result

    def summarise_tool_output(self, output: str, max_chars: int = 400) -> str:
        """Return output as-is if within budget, otherwise truncate with a note.

        No LLM call — simple heuristic truncation only.
        """
        if not output or len(output) <= max_chars:
            return output
        return output[:max_chars] + "... [output truncated]"

    def estimate_chars(self, text: str) -> int:
        """Return exact character count of text."""
        return len(text)

    def estimate_tokens(self, text: str) -> int:
        """Return a rough token estimate (chars / 4)."""
        return len(text) // 4
