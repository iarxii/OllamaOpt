"""
OllamaOpt Rich CLI Wrapper - Main entry point
A Claude/Gemini-style CLI interface for local Ollama models with comprehensive metrics
"""

import sys
import time
import threading
import logging
import os
import requests
from pathlib import Path
from typing import Optional, Generator

from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text
from rich.panel import Panel
from rich import box

from .metrics_collector import initialize_collector_static, get_collector, shutdown_collector
from .dashboard import Dashboard, render_welcome_screen, LatencyChart
from .chat_interface import ChatInterface, CommandHandler, StreamingResponseDisplay
from .formatters import IndicatorFormatter, format_duration
from .assets.logo_art import (
    OLLAMA_OPT_LOGO, OLLAMA_OPT_COMPACT,
    STATUS_INDICATORS, TIER_ICONS, get_spinner_frame
)

console = Console()

class OllamaOptCLI:
    """Main CLI application for OllamaOpt"""

    def __init__(
        self,
        api_base: str = "http://localhost:11434",
        backend_mode: str = "unknown",
        backend_label: str = "",
        gpu_active: bool = False,
    ):
        self.api_base = api_base
        self.backend_mode = backend_mode
        self.backend_label = backend_label or backend_mode
        self.gpu_active = gpu_active
        self.collector = None
        self.chat = None
        self.command_handler = None
        self.dashboard = None
        self.running = False
        self._spinner_frame = 0
        self._setup_logging()

    def _setup_logging(self):
        """Initialise session log at logs/cli_session.log"""
        try:
            os.makedirs("logs", exist_ok=True)
            logging.basicConfig(
                filename=os.path.join("logs", "cli_session.log"),
                level=logging.INFO,
                format="%(asctime)s %(levelname)s %(message)s",
                encoding="utf-8",
            )
        except Exception:
            pass  # Never crash the CLI over a logging failure

    def initialize(self) -> bool:
        """Initialize CLI components"""
        try:
            console.print("[cyan]Initializing OllamaOpt CLI...[/cyan]")

            # Log backend info
            logging.info(
                "CLI initializing — backend_mode=%s label=%s gpu_active=%s api=%s",
                self.backend_mode,
                self.backend_label,
                self.gpu_active,
                self.api_base,
            )

            # Warn loudly if we are in fallback mode
            if self.backend_mode == "fallback":
                console.print(
                    "\n[yellow bold]  ⚠  FALLBACK MODE[/yellow bold]"
                    " — [yellow]running without GPU optimisation.[/yellow]"
                )
                console.print(
                    "[yellow]  Token generation will be significantly slower.[/yellow]"
                )
                console.print(
                    "[yellow]  Run [cyan]preflight_checks.bat[/cyan][yellow] or "
                    "[cyan]start_ollama_server.bat[/cyan][yellow] for GPU acceleration.[/yellow]\n"
                )
                logging.warning("Running in fallback mode — no GPU optimisation active")

            # Check if Ollama server is reachable before doing anything else
            try:
                requests.get(f"{self.api_base}/api/tags", timeout=3)
            except requests.exceptions.ConnectionError:
                console.print(f"\n[red]✗ Cannot reach Ollama server at {self.api_base}[/red]")
                console.print("[yellow]  The Ollama service is not running.[/yellow]")
                console.print("[yellow]  Start it with:  ollama serve[/yellow]")
                console.print("[yellow]  Then re-run:    run_ollama_cli.bat[/yellow]")
                logging.error("Cannot reach Ollama server at %s", self.api_base)
                return False
            except requests.exceptions.Timeout:
                console.print(f"\n[red]✗ Ollama server timed out at {self.api_base}[/red]")
                console.print("[yellow]  Check that Ollama is running and responsive.[/yellow]")
                logging.error("Ollama server timed out at %s", self.api_base)
                return False

            # Collect model/hardware info once — no background thread, no probe loop
            self.collector = initialize_collector_static(self.api_base)

            # Initialize chat interface
            self.chat = ChatInterface(self.api_base)
            self.command_handler = CommandHandler(self.chat)
            self.dashboard = Dashboard()

            # Try to get models — server is confirmed running at this point
            models = self.chat.get_available_models()
            if not models:
                console.print("\n[red]✗ No models are installed in Ollama.[/red]")
                console.print("[yellow]  Pull a model first, for example:[/yellow]")
                console.print("[cyan]    ollama pull llama3.2:3b[/cyan]")
                console.print("[cyan]    ollama pull qwen2.5:7b[/cyan]")
                console.print("[cyan]    ollama pull qwen3:8b[/cyan]")
                logging.error("No models installed in Ollama")
                return False

            # Set first model as default
            default_model = models[0].get("name", "")
            if default_model:
                self.chat.set_model(default_model)
                console.print(f"[green]✓ Using model: {default_model}[/green]")
                logging.info("Active model: %s", default_model)

            console.print("[green]✓ Initialization complete[/green]\n")
            logging.info("Initialization complete")
            return True

        except Exception as e:
            console.print(f"[red]✗ Initialization failed: {e}[/red]")
            logging.exception("Initialization failed: %s", e)
            return False

    def show_intro(self):
        """Show a simple, plain-text welcome panel including backend status."""
        snapshot = self.collector.get_snapshot()
        tier = snapshot["hardware"]["tier"]
        model = snapshot["model"]["name"]
        size_gb = snapshot["model"]["size_gb"]

        # Choose colours based on backend health
        if self.backend_mode == "gpu_pipeline":
            backend_style = "green"
            backend_icon = "[green]GPU[/green]"
        elif self.backend_mode == "existing":
            backend_style = "cyan"
            backend_icon = "[cyan]Server[/cyan]"
        else:
            backend_style = "yellow"
            backend_icon = "[yellow]FALLBACK[/yellow]"

        lines = Text()
        lines.append("  OllamaOpt CLI\n", style="cyan bold")
        lines.append("  " + "-" * 44 + "\n", style="bright_black")
        lines.append(f"  Model    : ", style="white")
        lines.append(f"{model}  ({size_gb:.1f} GB)\n", style="cyan")
        lines.append(f"  Hardware : ", style="white")
        lines.append(f"{tier.upper()}\n", style="cyan")
        lines.append(f"  Backend  : ", style="white")
        lines.append(f"{self.backend_label}\n", style=backend_style)
        lines.append("  " + "-" * 44 + "\n", style="bright_black")
        lines.append("  /help  /models  /switch  /stats  /clear  /exit\n", style="dim white")

        border = "yellow" if self.backend_mode == "fallback" else "cyan"
        console.print(Panel(lines, border_style=border, padding=(0, 1)))

        # Prominent fallback warning repeated here so it stays visible after init messages scroll
        if self.backend_mode == "fallback":
            console.print(Panel(
                Text(
                    "  Running in FALLBACK mode — no GPU optimisation.\n"
                    "  Run preflight_checks.bat or start_ollama_server.bat\n"
                    "  to enable the Intel GPU pipeline.",
                    style="yellow",
                ),
                title="[yellow bold]WARNING[/yellow bold]",
                border_style="yellow",
                padding=(0, 1),
            ))

        console.print()

    def render_dashboard_header(self):
        """Render the dashboard header with metrics"""
        console.print(self.dashboard.render_header())
        console.print(self.dashboard.render_metrics())

    def get_user_input(self) -> str:
        """Get user input with styled prompt"""
        try:
            user_input = Prompt.ask("[cyan]▸ You[/cyan]", console=console)
            return user_input.strip()
        except KeyboardInterrupt:
            return "/exit"
        except EOFError:
            return "/exit"

    def process_response_streaming(self, response_generator: Generator) -> str:
        """Process streaming response with real-time display.

        Shows a 'Thinking...' panel while waiting for the first token so the
        user knows the model is working (critical for thinking models like
        DeepSeek R1 that have a long silent chain-of-thought phase).
        Records real generation latency for the metrics dashboard.
        """
        response_text = ""
        start_time = time.time()
        first_token_time: Optional[float] = None

        console.print()  # spacing before response

        thinking_panel = Panel(
            Text("⠋ Thinking…", style="yellow"),
            title="[dim green]Assistant[/dim green]",
            border_style="dim green",
        )

        from rich.live import Live
        with Live(thinking_panel, console=console, refresh_per_second=6) as live:
            spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            frame_idx = 0

            for token in response_generator:
                if first_token_time is None:
                    first_token_time = time.time()
                response_text += token
                frame_idx += 1

                display_text = Text(response_text, style="white")
                display_text.append(f" {spinner_frames[frame_idx % len(spinner_frames)]}", style="yellow")
                live.update(Panel(
                    display_text,
                    title="[green]Assistant[/green]",
                    border_style="green",
                ))

            # Final update — remove cursor spinner
            live.update(Panel(
                Text(response_text, style="white"),
                title="[green]● Assistant[/green]",
                border_style="green",
            ))

        # Record real generation latency into the metrics dashboard
        elapsed_ms = (time.time() - start_time) * 1000
        token_count = len(response_text.split())
        tokens_per_sec = (token_count / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0.0
        if self.collector:
            self.collector.record_generation_latency(elapsed_ms, tokens_per_sec)

        return response_text

    def handle_user_input(self, user_input: str):
        """Handle user input (command or chat message)"""
        if not user_input:
            return True

        # Exit commands must be checked first — handle_command() returns False
        # for /exit and /quit (to signal exit), so we cannot rely on its return
        # value to catch them; they would fall through to the chat path otherwise.
        if user_input.lower() in ["/exit", "/quit"]:
            return False

        # Other slash commands
        if self.command_handler.handle_command(user_input):
            return True

        # Regular chat message
        # Display user message
        console.print()
        from .formatters import MessageFormatter
        console.print(MessageFormatter.format_user_message(user_input))

        # Record in history
        self.chat.add_message("user", user_input)

        # Generate response with streaming
        try:
            response_gen = self.chat.stream_response(user_input)
            response_text = self.process_response_streaming(response_gen)

            # Record response in history
            self.chat.add_message("assistant", response_text)
            console.print()  # Add spacing

        except KeyboardInterrupt:
            self.chat.stop_streaming()
            console.print("\n[yellow]✓ Response interrupted[/yellow]\n")
        except Exception as e:
            console.print(f"\n[red]✗ Error: {str(e)}[/red]\n")

        return True

    def run_interactive_loop(self):
        """Main interactive CLI loop"""
        self.running = True
        self.show_intro()

        try:
            while self.running:
                # Get user input
                user_input = self.get_user_input()

                # Process input
                continue_running = self.handle_user_input(user_input)
                if not continue_running:
                    break

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Unexpected error: {e}[/red]")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup on exit"""
        console.print("\n[cyan]Shutting down...[/cyan]")
        logging.info("CLI shutdown")

        if self.collector:
            shutdown_collector()

        console.print("[green]✓ Goodbye![/green]")
        self.running = False

def main(
    api_base: str = "http://localhost:11434",
    backend_mode: str = "unknown",
    backend_label: str = "",
    gpu_active: bool = False,
):
    """Main entry point for the CLI"""

    cli = OllamaOptCLI(
        api_base=api_base,
        backend_mode=backend_mode,
        backend_label=backend_label,
        gpu_active=gpu_active,
    )

    # Initialize
    if not cli.initialize():
        sys.exit(1)

    # Run interactive loop
    cli.run_interactive_loop()

def cli_main():
    """Entry point for console script"""
    import argparse

    parser = argparse.ArgumentParser(
        description="OllamaOpt Rich CLI - Claude/Gemini-style interface for local Ollama models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ollama-cli                                Run with default settings (localhost:11434)
  ollama-cli --api http://localhost:11434   Use custom API endpoint
        """
    )

    parser.add_argument(
        "--api",
        default="http://localhost:11434",
        help="Ollama API endpoint (default: %(default)s)",
    )
    parser.add_argument(
        "--model",
        help="Default model to use (optional, will use first available)",
    )
    parser.add_argument(
        "--backend-mode",
        default=os.environ.get("OLLAMAOPT_BACKEND_MODE", "unknown"),
        dest="backend_mode",
        help="Backend mode set by the launcher (existing|gpu_pipeline|fallback)",
    )
    parser.add_argument(
        "--backend-label",
        default=os.environ.get("OLLAMAOPT_BACKEND_LABEL", ""),
        dest="backend_label",
        help="Human-readable backend label set by the launcher",
    )
    parser.add_argument(
        "--gpu-active",
        action="store_true",
        default=os.environ.get("OLLAMAOPT_GPU_ACTIVE", "0") == "1",
        dest="gpu_active",
        help="Set when the GPU pipeline is confirmed active",
    )

    args = parser.parse_args()

    try:
        main(
            api_base=args.api,
            backend_mode=args.backend_mode,
            backend_label=args.backend_label,
            gpu_active=args.gpu_active,
        )
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        logging.exception("Fatal error in cli_main: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    cli_main()
