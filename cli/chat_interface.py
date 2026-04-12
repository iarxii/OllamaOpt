"""
Chat interface with message I/O and streaming support with RAG, Memory, and Routing integration.
"""

import logging
import threading
import time
import requests
import json
from typing import Optional, Callable, Generator, List
from datetime import datetime

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .metrics_collector import get_collector
from .formatters import MessageFormatter, IndicatorFormatter

logger = logging.getLogger(__name__)
console = Console()


class ChatInterface:
    """Main chat interface with streaming support, RAG retrieval, and model routing."""

    def __init__(
        self,
        api_base: str = "http://localhost:11434",
        embedding_model: str = "nomic-embed-text",
        npu_model: str = "llama3.2:3b",
        gpu_model: str = "deepseek-r1:7b",
    ):
        self.api_base = api_base
        self.session = requests.Session()
        self.collector = get_collector()
        self.message_history = []
        self.current_model = None
        self.is_streaming = False

        # New integration components - initialized with graceful fallback
        self._init_integration_components(embedding_model, npu_model, gpu_model)

    def _init_integration_components(
        self, embedding_model: str, npu_model: str, gpu_model: str
    ) -> None:
        """Initialize RAG, Memory, ContextBuilder, and ModelRouter with graceful fallback."""
        # Defaults - will be replaced if components initialize successfully
        self.retriever = None
        self.episodic_memory = None
        self.session_state = None
        self.context_builder = None
        self.model_router = None

        # Storage for last retrieval/assembly results (for /context, /sources, /memory commands)
        self.last_retrieval_results: List = []
        self.last_assembled_context = None
        self.last_route_decision = None

        try:
            # 1. Initialize RAG components
            from .rag import QdrantVectorStore, OllamaEmbedder, Retriever

            store = QdrantVectorStore(
                collection_name="ollamaopt_docs",
                persist_dir="data/qdrant",
                embedding_dim=768,
            )
            embedder = OllamaEmbedder(
                api_base=self.api_base,
                model=embedding_model,
                timeout=30,
            )
            self.retriever = Retriever(
                store=store,
                embedder=embedder,
                top_k=5,
                score_threshold=0.3,
            )
            logger.info("RAG Retriever initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize RAG components: {e}")
            self.retriever = None

        try:
            # 2. Initialize Memory components
            from .memory import SessionState, EpisodicMemory

            self.session_state = SessionState()
            self.episodic_memory = EpisodicMemory(
                persist_dir="data/memory",
                api_base=self.api_base,
                embedding_model=embedding_model,
            )
            logger.info("Memory components initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Memory components: {e}")
            self.session_state = None
            self.episodic_memory = None

        try:
            # 3. Initialize Context Builder
            from .context import ContextBuilder, ContextPolicy

            policy = ContextPolicy()
            self.context_builder = ContextBuilder(policy=policy)
            # Set a default system prompt
            self.context_builder.set_system_prompt(
                "You are OllamaOpt, a helpful AI assistant running on Intel hardware. "
                "Use the provided context to ground your answers. "
                "Cite sources when using retrieved information."
            )
            logger.info("ContextBuilder initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize ContextBuilder: {e}")
            self.context_builder = None

        try:
            # 4. Initialize Model Router
            from .routing import ModelRouter

            available_models = self.get_available_model_names()
            self.model_router = ModelRouter(
                npu_model=npu_model,
                gpu_model=gpu_model,
                available_models=available_models,
            )
            logger.info("ModelRouter initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize ModelRouter: {e}")
            self.model_router = None

        # Log initialization summary
        status = {
            "retriever": self.retriever is not None,
            "episodic_memory": self.episodic_memory is not None,
            "session_state": self.session_state is not None,
            "context_builder": self.context_builder is not None,
            "model_router": self.model_router is not None,
        }
        logger.info(f"Integration components status: {status}")

    def get_available_model_names(self) -> List[str]:
        """Return list of available model names (strings only)."""
        models = self.get_available_models()
        return [m.get("name", "") for m in models if m.get("name")]

    def set_model(self, model_name: str):
        """Set the current model"""
        self.current_model = model_name

    def is_server_running(self) -> bool:
        """Check whether the Ollama server is reachable"""
        try:
            resp = self.session.get(f"{self.api_base}/api/tags", timeout=3)
            return resp.status_code == 200
        except requests.exceptions.ConnectionError:
            return False
        except Exception:
            return False

    def get_available_models(self) -> list:
        """Get list of available models from Ollama"""
        try:
            resp = self.session.get(f"{self.api_base}/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("models", [])
        except requests.exceptions.ConnectionError:
            pass  # Server not running — caller handles this via is_server_running()
        except Exception as e:
            console.print(f"[yellow]Warning: could not fetch models ({type(e).__name__})[/yellow]")
        return []

    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry"""
        try:
            console.print(f"[yellow]Pulling model {model_name}...[/yellow]")
            resp = self.session.post(
                f"{self.api_base}/api/pull",
                json={"name": model_name},
                stream=True,
                timeout=None
            )

            for line in resp.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        status = data.get("status", "")
                        if status:
                            console.print(f"[cyan]{status}[/cyan]", end="\r")
                    except json.JSONDecodeError:
                        pass

            console.print("[green]✓ Model pulled successfully[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error pulling model: {e}[/red]")
            return False

    def add_message(self, role: str, content: str, timestamp: Optional[datetime] = None):
        """Add a message to history"""
        if timestamp is None:
            timestamp = datetime.now()

        self.message_history.append({
            "role": role,
            "content": content,
            "timestamp": timestamp,
        })

        if role == "user":
            self.collector.record_message()

    def stream_response(self, prompt: str, on_token: Optional[Callable[[str], None]] = None) -> Generator[str, None, None]:
        """Stream a response from Ollama with callback for each token"""
        try:
            if not self.current_model:
                yield "[red]Error: No model selected[/red]"
                return

            self.is_streaming = True

            resp = self.session.post(
                f"{self.api_base}/api/generate",
                json={
                    "model": self.current_model,
                    "prompt": prompt,
                    "stream": True,
                },
                stream=True,
                timeout=None
            )

            full_response = ""
            token_count = 0

            for line in resp.iter_lines():
                if not self.is_streaming:
                    break

                if line:
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")

                        if token:
                            full_response += token
                            token_count += 1

                            # Simulate streaming delay for smooth display
                            if on_token:
                                on_token(token)

                            yield token

                        # Check if done
                        if data.get("done", False):
                            # Record metrics
                            eval_count = data.get("eval_count", 0)
                            self.collector.record_tokens_generated(eval_count)
                            break
                    except json.JSONDecodeError:
                        pass

            self.is_streaming = False
        except Exception as e:
            self.is_streaming = False
            yield f"[red]Error: {str(e)}[/red]"

    def generate_response(self, prompt: str) -> str:
        """Generate a complete response (non-streaming)"""
        try:
            if not self.current_model:
                return "[red]Error: No model selected[/red]"

            resp = self.session.post(
                f"{self.api_base}/api/generate",
                json={
                    "model": self.current_model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=30
            )

            if resp.status_code == 200:
                data = resp.json()
                response = data.get("response", "")
                eval_count = data.get("eval_count", 0)

                self.collector.record_tokens_generated(eval_count)

                return response
            else:
                return f"[red]Error: API returned {resp.status_code}[/red]"
        except requests.Timeout:
            return "[red]Error: Request timed out[/red]"
        except Exception as e:
            return f"[red]Error: {str(e)}[/red]"

    def stop_streaming(self):
        """Stop current streaming response"""
        self.is_streaming = False

    def clear_history(self):
        """Clear message history"""
        self.message_history = []

    def get_conversation_context(self, max_messages: int = 10) -> str:
        """Get recent conversation context for context window"""
        recent = self.message_history[-max_messages:]
        context = []

        for msg in recent:
            role = msg["role"]
            content = msg["content"]
            context.append(f"{role.capitalize()}: {content}")

        return "\n".join(context)

    def display_message(self, role: str, content: str, streaming: bool = False):
        """Display a message with appropriate formatting"""
        if role == "user":
            panel = MessageFormatter.format_user_message(content)
        elif role == "assistant":
            panel = MessageFormatter.format_assistant_message(content, finished=not streaming)
        elif role == "error":
            panel = MessageFormatter.format_error_message(content)
        else:
            panel = MessageFormatter.format_system_message(content)

        console.print(panel)

    # ------------------------------------------------------------------
    # Context-aware streaming (Phase 2 integration)
    # ------------------------------------------------------------------

    def stream_with_context(
        self,
        user_query: str,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> Generator[str, None, None]:
        """Retrieve context, build prompt, route model, and stream response.

        This method orchestrates the full RAG + Memory + Routing pipeline:
        1. Retrieve relevant documents using the RAG retriever
        2. Retrieve relevant memories from episodic memory
        3. Route the request to the appropriate model (NPU/GPU/CPU)
        4. Build the assembled context with budget enforcement
        5. Stream the response using the selected model

        Yields tokens for streaming display. Stores results for /context, /sources,
        and /memory commands.
        """
        try:
            self.is_streaming = True

            # 1. Retrieve documents from RAG
            self.last_retrieval_results = []
            retrieval_results = []
            if self.retriever is not None:
                try:
                    retrieval_results = self.retriever.retrieve(user_query)
                    self.last_retrieval_results = retrieval_results
                    if retrieval_results:
                        logger.info(f"RAG retrieved {len(retrieval_results)} chunks")
                except Exception as e:
                    logger.warning(f"RAG retrieval failed: {e}")

            # 2. Retrieve relevant memories
            memory_items = []
            if self.episodic_memory is not None and self.episodic_memory.is_available():
                try:
                    memory_items = self.episodic_memory.retrieve_relevant(
                        user_query, top_k=3, score_threshold=0.4
                    )
                    if memory_items:
                        logger.info(f"Episodic memory recalled {len(memory_items)} items")
                except Exception as e:
                    logger.warning(f"Episodic memory recall failed: {e}")

            # 3. Get tool outputs from session state (if available)
            tool_results = []
            if self.session_state is not None:
                try:
                    tool_results = [
                        {"tool_name": t["tool_name"], "output": t["output"]}
                        for t in self.session_state.recent_tool_outputs
                    ]
                except Exception as e:
                    logger.warning(f"Session state access failed: {e}")

            # 4. Build assembled context
            context_chars = 0
            assembled_context = None
            if self.context_builder is not None:
                try:
                    # Convert retrieval results to dict format expected by ContextBuilder
                    retrieved_chunks = [
                        {
                            "title": r.title,
                            "source_path": r.source_path,
                            "content": r.content,
                            "score": r.score,
                        }
                        for r in retrieval_results
                    ]

                    # Convert memory items to dict format
                    memory_dicts = [
                        {
                            "memory_id": getattr(m, "memory_id", ""),
                            "topic": getattr(m, "topic", ""),
                            "content": getattr(m, "content", ""),
                            "source": getattr(m, "source", ""),
                        }
                        for m in memory_items
                    ]

                    assembled_context = self.context_builder.build(
                        user_query=user_query,
                        chat_history=self.message_history,
                        retrieved_chunks=retrieved_chunks,
                        tool_results=tool_results,
                        memory_items=memory_dicts,
                    )
                    context_chars = assembled_context.total_chars
                    self.last_assembled_context = assembled_context
                    logger.info(
                        f"Context assembled: {context_chars} chars "
                        f"(budget: {assembled_context.context_stats.get('budget_used_pct', 0):.1f}%)"
                    )
                except Exception as e:
                    logger.warning(f"Context building failed: {e}")

            # 5. Route to appropriate model
            route_decision = None
            selected_model = self.current_model
            if self.model_router is not None:
                try:
                    route_decision = self.model_router.route(
                        query=user_query,
                        context_chars=context_chars,
                        requires_tool=bool(tool_results),
                        requires_synthesis=len(retrieval_results) > 2,
                    )
                    selected_model = route_decision.model
                    self.last_route_decision = route_decision
                    logger.info(f"Routed to {route_decision.path.value}: {route_decision.reason}")

                    # Apply NPU strict mode if routed to NPU
                    if (
                        route_decision.path.value == "npu"
                        and self.context_builder is not None
                        and self.context_builder.policy is not None
                    ):
                        self.context_builder.policy.apply_npu_mode()
                except Exception as e:
                    logger.warning(f"Model routing failed: {e}")

            # 6. Assemble final prompt string
            full_prompt = user_query
            if assembled_context is not None and self.context_builder is not None:
                try:
                    full_prompt = self.context_builder.assemble_prompt_string(
                        assembled_context, user_query
                    )
                except Exception as e:
                    logger.warning(f"Prompt assembly failed: {e}")

            # 7. Stream response using selected model
            if not selected_model:
                yield "[red]Error: No model selected[/red]"
                self.is_streaming = False
                return

            resp = self.session.post(
                f"{self.api_base}/api/generate",
                json={
                    "model": selected_model,
                    "prompt": full_prompt,
                    "stream": True,
                },
                stream=True,
                timeout=None,
            )

            full_response = ""
            token_count = 0

            for line in resp.iter_lines():
                if not self.is_streaming:
                    break

                if line:
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")

                        if token:
                            full_response += token
                            token_count += 1

                            if on_token:
                                on_token(token)

                            yield token

                        if data.get("done", False):
                            eval_count = data.get("eval_count", 0)
                            self.collector.record_tokens_generated(eval_count)
                            break
                    except json.JSONDecodeError:
                        pass

            self.is_streaming = False

            # 8. Store memory of this interaction (non-blocking)
            if self.episodic_memory is not None and self.episodic_memory.is_available():
                try:
                    # Add the response to episodic memory asynchronously
                    memory_content = f"User asked: {user_query}\nAssistant responded: {full_response[:500]}"
                    self.episodic_memory.add_memory(
                        content=memory_content,
                        topic=self.session_state.current_topic if self.session_state else "",
                        source="conversation",
                    )
                except Exception as e:
                    logger.warning(f"Storing episodic memory failed: {e}")

        except Exception as e:
            self.is_streaming = False
            logger.error(f"stream_with_context failed: {e}")
            yield f"[red]Error: {str(e)}[/red]"

    # ------------------------------------------------------------------
    # Helper methods for command inspection
    # ------------------------------------------------------------------

    def get_context_stats(self) -> dict:
        """Return context assembly stats for /context command."""
        if self.last_assembled_context is None:
            return {"error": "No context assembled yet"}
        return self.context_builder.get_stats(self.last_assembled_context)

    def get_sources_info(self) -> List[dict]:
        """Return retrieved sources for /sources command."""
        if not self.last_retrieval_results:
            return []
        return [
            {
                "title": r.title,
                "source_path": r.source_path,
                "score": r.score,
                "chunk_id": r.chunk_id,
            }
            for r in self.last_retrieval_results
        ]

    def get_memory_info(self) -> dict:
        """Return episodic memory info for /memory command."""
        if self.episodic_memory is None:
            return {"error": "Episodic memory not available"}
        if not self.episodic_memory.is_available():
            return {"error": "Episodic memory unavailable (Qdrant not initialized)"}
        return {
            "is_available": True,
            "persist_dir": self.episodic_memory.persist_dir,
            "embedding_model": self.episodic_memory.embedding_model,
            "last_recall_count": len(self.last_retrieval_results)
            if hasattr(self, "last_retrieval_results")
            else 0,
        }

class StreamingResponseDisplay:
    """Handles real-time display of streaming responses"""

    def __init__(self, console_instance: Console = None):
        self.console = console_instance or console
        self.buffer = ""
        self.token_count = 0
        self.start_time = None
        self.last_update_time = 0

    def on_token(self, token: str):
        """Handle incoming token from stream"""
        self.buffer += token
        self.token_count += 1

        # Update display every 20 tokens or after a delay
        now = time.time()
        if (self.token_count % 20 == 0 or now - self.last_update_time > 0.5):
            self._display_chunk()
            self.last_update_time = now

    def on_complete(self):
        """Handle completion of stream"""
        if self.buffer:
            self._display_chunk(final=True)

    def _display_chunk(self, final: bool = False):
        """Display accumulated buffer"""
        if not self.buffer:
            return

        # Simple display with cursor
        suffix = "" if final else " ◐"
        content = Text(self.buffer + suffix, style="white")

        # In a real implementation, this would update in-place
        # For now, we'll print normally
        if final:
            self.console.print(content)

    def reset(self):
        """Reset for new streaming response"""
        self.buffer = ""
        self.token_count = 0
        self.start_time = time.time()
        self.last_update_time = 0

class CommandHandler:
    """Handles built-in CLI commands"""

    def __init__(self, chat: ChatInterface):
        self.chat = chat
        self.collector = get_collector()

    def handle_command(self, command: str) -> bool:
        """Handle command if it starts with /. Return True if handled."""
        if not command.startswith("/"):
            return False

        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            self._cmd_help()
        elif cmd == "/models":
            self._cmd_models()
        elif cmd == "/switch":
            self._cmd_switch(arg)
        elif cmd == "/stats":
            self._cmd_stats()
        elif cmd == "/info":
            self._cmd_info()
        elif cmd == "/clear":
            self._cmd_clear()
        elif cmd == "/context":
            self._cmd_context()
        elif cmd == "/sources":
            self._cmd_sources()
        elif cmd == "/memory":
            self._cmd_memory()
        elif cmd == "/exit" or cmd == "/quit":
            return False
        else:
            console.print(f"[yellow]Unknown command: {cmd}[/yellow]")

        return True

    def _cmd_help(self):
        """Show help"""
        from .formatters import HelpFormatter
        console.print(HelpFormatter.format_help_panel())

    def _cmd_models(self):
        """List available models"""
        models = self.chat.get_available_models()

        if not models:
            console.print("[yellow]No models available[/yellow]")
            return

        from rich.table import Table
        table = Table(title="[cyan]Available Models[/cyan]", show_header=True, header_style="bold cyan")
        table.add_column("Model", style="cyan")
        table.add_column("Size", style="white")
        table.add_column("Status", style="white")

        for model in models:
            name = model.get("name", "Unknown")
            size_gb = model.get("size", 0) / (1024**3)
            status = "[green]Loaded[/green]" if model.get("details", {}).get("loaded") else "[dim]Available[/dim]"

            table.add_row(name, f"{size_gb:.1f} GB", status)

        console.print(table)

    def _cmd_switch(self, model_name: str):
        """Switch to a different model"""
        if not model_name:
            console.print("[yellow]Usage: /switch <model_name>[/yellow]")
            return

        self.chat.set_model(model_name)
        console.print(f"[green]✓ Switched to model: {model_name}[/green]")

    def _cmd_stats(self):
        """Show detailed session statistics"""
        from .dashboard import Dashboard
        dashboard = Dashboard()
        console.print(dashboard.render_full_metrics_panel())

    def _cmd_info(self):
        """Show current model and system info"""
        snapshot = self.collector.get_snapshot()

        from rich.table import Table
        table = Table(show_header=False, show_footer=False, padding=(0, 1))
        table.add_column(style="bold cyan", width=15)
        table.add_column(style="white")

        model = snapshot["model"]
        hardware = snapshot["hardware"]
        perf = snapshot["performance"]

        table.add_row("Current Model:", model["name"] or "None")
        table.add_row("Model Size:", f"{model['size_gb']:.1f} GB")
        table.add_row("Hardware Tier:", hardware["tier"].upper())
        table.add_row("Latest Latency:", f"{perf['latency_ms']:.1f} ms")
        table.add_row("Avg Latency:", f"{perf['avg_latency_ms']:.1f} ms")

        console.print(Panel(table, title="[cyan]Session Info[/cyan]", border_style="cyan"))

    def _cmd_clear(self):
        """Clear message history"""
        self.chat.clear_history()
        console.print("[green]✓ Chat history cleared[/green]")

    def _cmd_context(self):
        """Show assembled context stats from the last query."""
        stats = self.chat.get_context_stats()

        if "error" in stats:
            console.print(f"[yellow]{stats['error']}[/yellow]")
            return

        table = Table(
            title="[cyan]Context Assembly Stats[/cyan]",
            show_header=False,
            show_footer=False,
            padding=(0, 2),
        )
        table.add_column(style="bold cyan", width=20)
        table.add_column(style="white")

        table.add_row("System prompt chars:", f"{stats.get('system_chars', 0):,}")
        table.add_row("Retrieved docs chars:", f"{stats.get('retrieved_chars', 0):,}")
        table.add_row("Tool output chars:", f"{stats.get('tool_chars', 0):,}")
        table.add_row("Memory chars:", f"{stats.get('memory_chars', 0):,}")
        table.add_row("History chars:", f"{stats.get('history_chars', 0):,}")
        table.add_row("[bold]Total chars:[/bold]", f"[bold]{stats.get('total_chars', 0):,}[/bold]")
        table.add_row("Sources used:", f"{stats.get('sources_count', 0)}")
        table.add_row(
            "Budget used:",
            f"{stats.get('budget_used_pct', 0):.1f}% {'[yellow](truncated)[/yellow]' if stats.get('was_truncated') else ''}"
        )

        console.print(Panel(table, border_style="cyan"))

        # Show routing decision if available
        if self.chat.last_route_decision:
            route = self.chat.last_route_decision
            route_str = f"Model: {route.model} | Path: {route.path.value.upper()} | Reason: {route.reason}"
            console.print(f"[dim]{route_str}[/dim]")

    def _cmd_sources(self):
        """List retrieved document chunks from the last query."""
        sources = self.chat.get_sources_info()

        if not sources:
            console.print("[yellow]No sources retrieved yet[/yellow]")
            return

        table = Table(
            title=f"[cyan]Retrieved Sources ({len(sources)})[/cyan]",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Title", style="white", no_wrap=False)
        table.add_column("Source Path", style="dim", no_wrap=False)
        table.add_column("Score", style="cyan", justify="right")

        for src in sources:
            title = (src.get("title") or "Untitled")[:40]
            path = (src.get("source_path") or "")[:30]
            score = f"{src.get('score', 0.0):.2f}"
            table.add_row(title, path, score)

        console.print(table)

    def _cmd_memory(self):
        """Show episodic memory status and recall info."""
        info = self.chat.get_memory_info()

        if "error" in info:
            console.print(f"[yellow]{info['error']}[/yellow]")
            return

        table = Table(
            title="[cyan]Episodic Memory Status[/cyan]",
            show_header=False,
            show_footer=False,
            padding=(0, 2),
        )
        table.add_column(style="bold cyan", width=20)
        table.add_column(style="white")

        table.add_row("Status:", "[green]Available[/green]")
        table.add_row("Persist directory:", info.get("persist_dir", "N/A"))
        table.add_row("Embedding model:", info.get("embedding_model", "N/A"))
        table.add_row("Last recall count:", str(info.get("last_recall_count", 0)))

        console.print(Panel(table, border_style="cyan"))
