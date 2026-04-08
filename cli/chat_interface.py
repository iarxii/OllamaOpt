"""
Chat interface with message I/O and streaming support
"""

import threading
import time
import requests
import json
from typing import Optional, Callable, Generator
from datetime import datetime

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.prompt import Prompt

from .metrics_collector import get_collector
from .formatters import MessageFormatter, IndicatorFormatter

console = Console()

class ChatInterface:
    """Main chat interface with streaming support"""

    def __init__(self, api_base: str = "http://localhost:11434"):
        self.api_base = api_base
        self.session = requests.Session()
        self.collector = get_collector()
        self.message_history = []
        self.current_model = None
        self.is_streaming = False

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
