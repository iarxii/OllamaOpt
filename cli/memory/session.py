"""Short-term session state — current goal, topic, tool outputs, follow-ups."""

from datetime import datetime, timezone


class SessionState:
    """Tracks the current short-term context of an active CLI session.

    Holds the user's current goal, active topic, recent tool outputs (capped at 5),
    and unresolved follow-up questions (capped at 10). All fields are plain Python
    types so the state can be freely serialised or passed into context builders.
    """

    def __init__(self) -> None:
        self.current_goal: str = ""
        self.current_topic: str = ""
        self.recent_tool_outputs: list = []   # max 5 entries
        self.unresolved_followups: list = []  # max 10 questions
        self._created_at: datetime = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Setters
    # ------------------------------------------------------------------

    def set_goal(self, goal: str) -> None:
        """Set or replace the current session goal."""
        self.current_goal = goal

    def set_topic(self, topic: str) -> None:
        """Set or replace the current conversation topic."""
        self.current_topic = topic

    def add_tool_output(self, tool_name: str, output: str) -> None:
        """Record a tool result, truncating output to 500 chars. Keeps last 5."""
        entry = {
            "tool_name": tool_name,
            "output": output[:500],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.recent_tool_outputs.append(entry)
        if len(self.recent_tool_outputs) > 5:
            self.recent_tool_outputs = self.recent_tool_outputs[-5:]

    def add_followup(self, question: str) -> None:
        """Append an unresolved follow-up question. Keeps max 10."""
        self.unresolved_followups.append(question)
        if len(self.unresolved_followups) > 10:
            self.unresolved_followups = self.unresolved_followups[-10:]

    # ------------------------------------------------------------------
    # Clearers
    # ------------------------------------------------------------------

    def clear_followups(self) -> None:
        """Remove all pending follow-up questions."""
        self.unresolved_followups = []

    def clear_tool_outputs(self) -> None:
        """Remove all recorded tool outputs."""
        self.recent_tool_outputs = []

    # ------------------------------------------------------------------
    # Context formatting
    # ------------------------------------------------------------------

    def to_context_string(self, max_chars: int = 400) -> str:
        """Return a compact formatted summary of the current session state.

        Format::

            [Session State]
            Goal: <current_goal or "none">
            Topic: <current_topic or "none">
            Recent tools: <comma-joined tool names or "none">
            Follow-ups: <first 3 questions, each on its own line>

        The result is hard-truncated to *max_chars*.
        """
        tool_names = (
            ", ".join(t["tool_name"] for t in self.recent_tool_outputs)
            if self.recent_tool_outputs
            else "none"
        )

        followups = self.unresolved_followups[:3]
        if followups:
            followup_str = "\n  ".join(f"- {q}" for q in followups)
        else:
            followup_str = "none"

        result = (
            "[Session State]\n"
            f"Goal: {self.current_goal or 'none'}\n"
            f"Topic: {self.current_topic or 'none'}\n"
            f"Recent tools: {tool_names}\n"
            f"Follow-ups: {followup_str}"
        )
        return result[:max_chars]

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a fully serialisable snapshot of the session state."""
        return {
            "current_goal": self.current_goal,
            "current_topic": self.current_topic,
            "recent_tool_outputs": list(self.recent_tool_outputs),
            "unresolved_followups": list(self.unresolved_followups),
            "created_at": self._created_at.isoformat(),
        }
