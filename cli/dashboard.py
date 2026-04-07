"""
Dashboard layout and real-time metrics display
"""

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn
import time
from datetime import datetime

from .metrics_collector import get_collector
from .assets.logo_art import (
    OLLAMA_OPT_LOGO, STATUS_INDICATORS,
    create_latency_bar, create_system_bar, create_token_meter,
    get_spinner_frame, ColorPalette, TIER_ICONS
)
from .formatters import format_duration, IndicatorFormatter

console = Console()

class Dashboard:
    """Main dashboard display with real-time metrics"""
    
    def __init__(self):
        self.collector = get_collector()
        self.spinner_frame = 0
        
    def create_layout(self) -> Layout:
        """Create the main dashboard layout"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=15),
            Layout(name="metrics", size=5),
            Layout(name="spacer", size=1),
        )
        
        return layout
    
    def render_header(self) -> Panel:
        """Render the header with logo and status"""
        self.spinner_frame += 1
        
        content = Text()
        content.append(OLLAMA_OPT_LOGO, style="cyan")
        
        snapshot = self.collector.get_snapshot()
        model_name = snapshot["model"]["name"]
        tier = snapshot["hardware"]["tier"]
        
        # Status line
        status_line = Text()
        status_line.append(f"\n  {STATUS_INDICATORS['connected']} ", style="green")
        status_line.append(f"Model: {model_name} ", style="white")
        status_line.append(f"| Tier: {TIER_ICONS.get(tier, '❓')} ", style="white")
        status_line.append(f"{tier.upper()}", style="cyan bold")
        
        content.append(status_line)
        
        return Panel(
            content,
            border_style="cyan",
            style="black",
            expand=False,
        )
    
    def render_metrics(self) -> Table:
        """Render condensed metrics row"""
        snapshot = self.collector.get_snapshot()
        metrics = snapshot["performance"]
        system = snapshot["system"]
        
        table = Table(show_header=False, show_footer=False, padding=(0, 1), expand=False)
        table.add_column(style="white", no_wrap=True)
        
        # Build metrics string
        latency = metrics["latency_ms"]
        tokens_ps = metrics["tokens_per_sec"]
        cpu = system["cpu_percent"]
        vram = system["vram_percent"]
        
        # Create formatted metric row
        metric_row = Text()
        metric_row.append("⚡ ", style="cyan")
        
        # Latency
        if latency > 0:
            latency_color = "green" if latency < 300 else "yellow" if latency < 500 else "red"
            metric_row.append(f"{latency:6.1f}ms ", style=latency_color)
        else:
            metric_row.append(f"{'—':>6}ms ", style="dim white")
        
        metric_row.append("| ")
        
        # Tokens/sec
        tokens_color = "green" if tokens_ps > 15 else "yellow" if tokens_ps > 8 else "red"
        metric_row.append(f"{tokens_ps:5.1f}t/s ", style=tokens_color)
        
        metric_row.append("| ")
        
        # CPU
        cpu_color = "green" if cpu < 70 else "yellow" if cpu < 85 else "red"
        metric_row.append(f"CPU:{cpu:5.1f}% ", style=cpu_color)
        
        metric_row.append("| ")
        
        # VRAM
        vram_color = "green" if vram < 75 else "yellow" if vram < 90 else "red"
        metric_row.append(f"VRAM:{vram:5.1f}% ", style=vram_color)
        
        # Uptime
        uptime = snapshot["session"]["uptime_seconds"]
        metric_row.append("| ")
        metric_row.append(f"⏱ {format_duration(uptime)}", style="white")
        
        table.add_row(metric_row)
        
        return table
    
    def render_full_metrics_panel(self) -> Panel:
        """Render full metrics panel with detailed info"""
        snapshot = self.collector.get_snapshot()
        
        model = snapshot["model"]
        hardware = snapshot["hardware"]
        perf = snapshot["performance"]
        system = snapshot["system"]
        session = snapshot["session"]
        
        # Create detailed table
        table = Table(show_header=False, show_footer=False, padding=(0, 1))
        table.add_column(style="bold cyan", width=15)
        table.add_column(style="white")
        
        # Model info
        table.add_row("Model:", model["name"] or "—")
        table.add_row("Size:", f"{model['size_gb']:.1f} GB")
        table.add_row("Quantization:", model["quantization"])
        
        table.add_row("", "")  # Separator
        
        # Hardware
        hardware_text = f"{hardware['tier'].upper()} - {hardware['cpu_model']}"
        if hardware["gpu_detected"]:
            hardware_text += " (GPU Detected)"
        table.add_row("Hardware:", hardware_text)
        
        table.add_row("", "")  # Separator
        
        # Performance
        avg_lat = perf["avg_latency_ms"]
        lat_color = "green" if avg_lat < 300 else "yellow" if avg_lat < 500 else "red"
        table.add_row("Avg Latency:", f"[{lat_color}]{avg_lat:.1f}ms[/{lat_color}]")
        table.add_row("Latency Trend:", perf["latency_trend"])
        table.add_row("Tokens/Sec:", f"{perf['tokens_per_sec']:.1f}")
        
        table.add_row("", "")  # Separator
        
        # System
        table.add_row("CPU Usage:", f"{system['cpu_percent']:.1f}%")
        table.add_row("VRAM Usage:", f"{system['vram_used_gb']:.1f}/{system['vram_total_gb']:.1f} GB ({system['vram_percent']:.1f}%)")
        
        table.add_row("", "")  # Separator
        
        # Session
        table.add_row("Messages:", str(session["message_count"]))
        table.add_row("Tokens Generated:", f"{session['total_tokens']:,}")
        table.add_row("Session Duration:", format_duration(session["uptime_seconds"]))
        
        return Panel(table, title="[cyan]Session Metrics[/cyan]", border_style="cyan", padding=(1, 1))

class LatencyChart:
    """Real-time latency chart visualization"""
    
    def __init__(self, width: int = 40, height: int = 5):
        self.width = width
        self.height = height
        self.collector = get_collector()
    
    def render(self) -> str:
        """Render latency chart as ASCII art"""
        history = self.collector.latency_history
        
        if not history:
            return "[dim]No latency data yet...[/dim]"
        
        # Normalize to chart height
        min_val = min(history)
        max_val = max(history)
        range_val = max_val - min_val if max_val > min_val else 1
        
        # Sampling: take last `width` points
        sample_size = max(1, len(history) // self.width)
        samples = history[::sample_size]
        if len(samples) < self.width:
            samples = history[-(self.width):]  # Pad with whatever we have
            # Pad with spaces
            samples = [None] * (self.width - len(samples)) + samples
        
        # Create chart
        lines = []
        for row in range(self.height):
            line = ""
            threshold = max_val - (row / self.height) * range_val
            
            for val in samples:
                if val is None:
                    line += " "
                elif val >= threshold:
                    line += "▄"
                else:
                    line += " "
            
            lines.append(line)
        
        # Add scale
        chart_str = "\n".join(lines)
        scale = f"[dim]{max_val:.0f}ms[/dim] " + chart_str + f" [dim]{min_val:.0f}ms[/dim]"
        
        return scale

def render_welcome_screen() -> None:
    """Render welcome screen with instructions"""
    from .assets.logo_art import OLLAMA_OPT_COMPACT
    
    content = Text()
    content.append(OLLAMA_OPT_COMPACT + "\n\n", style="cyan")
    
    content.append("Welcome to the OllamaOpt CLI\n", style="bold cyan")
    content.append("─" * 50 + "\n\n", style="bright_black")
    
    instructions = [
        ("Type a message to chat with the AI model", "white"),
        ("/help to see all available commands", "cyan"),
        ("/models to list available models", "cyan"),
        ("CTRL+C to exit the CLI", "yellow"),
        ("", ""),
        ("Tip: Use multi-line input by pressing SHIFT+ENTER", "dim white"),
    ]
    
    for text, style in instructions:
        if text:
            content.append(f"  • {text}\n", style=style)
        else:
            content.append("\n")
    
    console.print(Panel(content, border_style="cyan", padding=(1, 2)))
