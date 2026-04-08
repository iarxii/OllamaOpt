"""
Text formatters and response styling for CLI output
"""

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
import re

console = Console()

class ResponseFormatter:
    """Formats and styles responses with syntax highlighting"""
    
    @staticmethod
    def detect_code_blocks(text: str) -> list:
        """Detect code blocks in text (```language ... ```)"""
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        return matches
    
    @staticmethod
    def format_response(text: str, stream_mode: bool = False) -> str:
        """Format response text with minimal processing for streaming"""
        return text
    
    @staticmethod
    def highlight_code(code: str, language: str = "python") -> Syntax:
        """Create a Syntax object for code highlighting"""
        try:
            return Syntax(code, language, theme="monokai", line_numbers=True, word_wrap=True)
        except Exception:
            return Syntax(code, "text", line_numbers=True, word_wrap=True)
    
    @staticmethod
    def format_markdown_simple(text: str) -> Text:
        """Simple markdown formatting (bold, italic, code)"""
        result = Text()
        i = 0
        while i < len(text):
            # Bold **text**
            if i < len(text) - 1 and text[i:i+2] == "**":
                end = text.find("**", i + 2)
                if end != -1:
                    result.append(text[i+2:end], style="bold white")
                    i = end + 2
                    continue
            
            # Italic *text*
            if text[i] == "*" and i > 0 and text[i-1] != "*":
                end = text.find("*", i + 1)
                if end != -1 and end < len(text) - 1 and text[end+1] != "*":
                    result.append(text[i+1:end], style="italic white")
                    i = end + 1
                    continue
            
            # Inline code `text`
            if text[i] == "`":
                end = text.find("`", i + 1)
                if end != -1:
                    result.append(text[i+1:end], style="cyan")
                    i = end + 1
                    continue
            
            result.append(text[i])
            i += 1
        
        return result

class MessageFormatter:
    """Formats chat messages for display"""
    
    @staticmethod
    def format_user_message(text: str, max_width: int = 80) -> Panel:
        """Format and display user message in a panel"""
        content = Text(text, style="white")
        return Panel(
            content,
            title="[cyan]You[/cyan]",
            border_style="cyan",
            expand=False,
            padding=(0, 1),
        )
    
    @staticmethod
    def format_assistant_message(text: str, max_width: int = 80, finished: bool = True) -> Panel:
        """Format and display assistant message in a panel"""
        suffix = "" if finished else " [dim]...[/dim]"
        
        # Try to detect code blocks
        code_blocks = ResponseFormatter.detect_code_blocks(text)
        
        if code_blocks:
            # If there are code blocks, return formatted content
            content = MessageFormatter._format_with_code_blocks(text)
        else:
            content = Text(text + suffix, style="white")
        
        status = "●" if finished else "◐"
        status_style = "green" if finished else "yellow"
        
        return Panel(
            content,
            title=f"[{status_style}]{status}[/{status_style}] [green]Assistant[/green]",
            border_style="green",
            expand=False,
            padding=(0, 1),
        )
    
    @staticmethod
    def _format_with_code_blocks(text: str) -> Text:
        """Format text with code block detection"""
        result = Text()
        
        pattern = r'```(\w+)?\n(.*?)```'
        last_end = 0
        
        for match in re.finditer(pattern, text, re.DOTALL):
            # Add text before code block
            if match.start() > last_end:
                result.append(text[last_end:match.start()])
            
            language = match.group(1) or "text"
            code = match.group(2).strip()
            
            # Add formatted code block
            result.append(f"\n[{language}]\n{code}\n[/{language}]\n", style="dim cyan")
            last_end = match.end()
        
        # Add remaining text
        if last_end < len(text):
            result.append(text[last_end:])
        
        return result
    
    @staticmethod
    def format_error_message(error: str) -> Panel:
        """Format error message"""
        return Panel(
            Text(error, style="white"),
            title="[red]❌ Error[/red]",
            border_style="red",
            expand=False,
            padding=(0, 1),
        )
    
    @staticmethod
    def format_system_message(message: str) -> Panel:
        """Format system message"""
        return Panel(
            Text(message, style="white"),
            title="[yellow]ℹ️ System[/yellow]",
            border_style="yellow",
            expand=False,
            padding=(0, 1),
        )

class IndicatorFormatter:
    """Formats status indicators and progress"""
    
    @staticmethod
    def format_connection_status(connected: bool) -> str:
        """Format connection status indicator"""
        if connected:
            return "[green]🟢[/green] [green]Connected[/green]"
        else:
            return "[red]🔴[/red] [red]Disconnected[/red]"
    
    @staticmethod
    def format_generation_spinner(frame: int) -> str:
        """Format generation progress spinner"""
        frames = ["◐", "◓", "◑", "◒"]
        return f"[yellow]{frames[frame % len(frames)]}[/yellow]"
    
    @staticmethod
    def format_memory_warning(vram_percent: float) -> str:
        """Format memory pressure warning"""
        if vram_percent > 90:
            return "[red]⚠️  Critical VRAM[/red]"
        elif vram_percent > 80:
            return "[yellow]⚠️  High VRAM[/yellow]"
        else:
            return "[green]✓ VRAM OK[/green]"
    
    @staticmethod
    def format_latency_warning(latency_ms: float) -> str:
        """Format latency status"""
        if latency_ms > 500:
            return f"[red]⚠️  {latency_ms:.0f}ms[/red]"
        elif latency_ms > 300:
            return f"[yellow]⚡ {latency_ms:.0f}ms[/yellow]"
        else:
            return f"[green]✓ {latency_ms:.0f}ms[/green]"

class HelpFormatter:
    """Formats help text and command information"""
    
    @staticmethod
    def format_help_panel() -> Table:
        """Format help command reference"""
        table = Table(title="[cyan bold]Available Commands[/cyan bold]", show_header=True, header_style="bold cyan")
        table.add_column("Command", style="cyan", width=20)
        table.add_column("Description", style="white")
        
        commands = [
            ("/models", "List available models with sizes"),
            ("/switch <model>", "Switch to a different model"),
            ("/stats", "Show detailed session statistics"),
            ("/clear", "Clear chat history"),
            ("/info", "Show current model and system info"),
            ("/help", "Show this help message"),
            ("/exit", "Exit the CLI"),
        ]
        
        for cmd, desc in commands:
            table.add_row(cmd, desc)
        
        return table

def format_duration(seconds: float) -> str:
    """Format duration in seconds to readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = seconds / 60
        return f"{mins:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def format_size(bytes_val: float) -> str:
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f}PB"

def format_number(num: float, decimals: int = 2) -> str:
    """Format number with specified decimal places"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.{decimals}f}M"
    elif num >= 1_000:
        return f"{num/1_000:.{decimals}f}K"
    else:
        return f"{num:.{decimals}f}"
