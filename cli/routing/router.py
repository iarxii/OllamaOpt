"""Model router — routes tasks to NPU, GPU, or CPU compute path."""

from dataclasses import dataclass
from enum import Enum


class ComputePath(Enum):
    NPU = "npu"
    GPU = "gpu"
    CPU = "cpu"


@dataclass
class RouteDecision:
    path: ComputePath
    model: str
    reason: str


class ModelRouter:
    """Routes inference tasks to the appropriate compute path based on query characteristics.

    Decision hierarchy (highest priority first):
    1. GPU  — synthesis required, large context (>1500 chars), or tool use needed.
    2. NPU  — short grounded queries with small context (<=1500 chars).
    3. CPU  — fallback when no other path applies or preferred model unavailable.
    """

    def __init__(
        self,
        npu_model: str = "llama3.2:3b",
        gpu_model: str = "deepseek-r1:7b",
        cpu_model: str = "llama3.2:3b",
        available_models: list = None,
    ):
        self.npu_model = npu_model
        self.gpu_model = gpu_model
        self.cpu_model = cpu_model
        self.available_models: list = available_models or []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(
        self,
        query: str,
        context_chars: int = 0,
        requires_tool: bool = False,
        requires_synthesis: bool = False,
    ) -> RouteDecision:
        """Select a compute path and model for the given query characteristics.

        Rules applied in priority order:
        - GPU  when: requires_synthesis OR context_chars > 1500 OR requires_tool
        - NPU  when: context_chars <= 1500 AND NOT requires_synthesis
        - CPU  otherwise (fallback)

        If the chosen model is not in available_models the first available
        model is substituted and the reason string is annotated accordingly.
        """
        if requires_synthesis or context_chars > 1500 or requires_tool:
            chosen_path = ComputePath.GPU
            chosen_model = self.gpu_model
            reason = self._build_gpu_reason(requires_synthesis, context_chars, requires_tool)
        elif context_chars <= 1500 and not requires_synthesis:
            chosen_path = ComputePath.NPU
            chosen_model = self.npu_model
            reason = "short grounded answer"
        else:
            chosen_path = ComputePath.CPU
            chosen_model = self.cpu_model
            reason = "CPU fallback"

        chosen_model, reason = self._validate_model(chosen_model, reason)
        return RouteDecision(path=chosen_path, model=chosen_model, reason=reason)

    def route_for_indexing(self) -> RouteDecision:
        """Always route summarisation / indexing tasks to GPU (or CPU if unavailable)."""
        model = self.gpu_model
        path = ComputePath.GPU
        reason = "background indexing/summarization"

        if self.available_models and model not in self.available_models:
            fallback = self.available_models[0]
            reason += f" (model {model!r} unavailable, using {fallback!r})"
            model = fallback
            path = ComputePath.CPU

        return RouteDecision(path=path, model=model, reason=reason)

    def format_decision(self, decision: RouteDecision) -> str:
        """Return a Rich-markup string summarising the routing decision."""
        _path_colour = {
            ComputePath.NPU: "cyan",
            ComputePath.GPU: "magenta",
            ComputePath.CPU: "yellow",
        }
        colour = _path_colour.get(decision.path, "white")
        label = decision.path.value.upper()
        return f"[{colour}]{label}[/{colour}] → {decision.model} ({decision.reason})"

    def update_available_models(self, models: list) -> None:
        """Replace the cached list of models currently pulled in Ollama."""
        self.available_models = list(models)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_model(self, model: str, reason: str) -> tuple:
        """If model is not in available_models, substitute the first available one."""
        if not self.available_models:
            # No list provided — trust the caller's model name as-is.
            return model, reason
        if model not in self.available_models:
            fallback = self.available_models[0]
            reason = f"{reason} (model {model!r} unavailable, using {fallback!r})"
            return fallback, reason
        return model, reason

    def _build_gpu_reason(
        self,
        requires_synthesis: bool,
        context_chars: int,
        requires_tool: bool,
    ) -> str:
        """Compose a human-readable reason string for a GPU routing decision."""
        parts = []
        if requires_synthesis:
            parts.append("synthesis required")
        if context_chars > 1500:
            parts.append(f"large context ({context_chars} chars)")
        if requires_tool:
            parts.append("tool use")
        return ", ".join(parts) if parts else "GPU path"
