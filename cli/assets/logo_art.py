"""
ASCII art and branding assets for OllamaOpt CLI
"""

OLLAMA_OPT_LOGO = """
    █████████████████████████████████████████████████████████████
    ██                                                         ██
    ██    ██████╗ ██╗      ██╗      █████╗ ███╗   ███╗ █████╗  ██
    ██   ██╔═══██╗██║      ██║     ██╔══██╗████╗ ████║██╔══██╗ ██
    ██   ██║   ██║██║      ██║     ███████║██╔████╔██║███████║ ██
    ██   ██║   ██║██║      ██║     ██╔══██║██║╚██╔╝██║██╔══██║ ██
    ██    ██████╔╝███████╗ ███████╗██║  ██║██║ ╚═╝ ██║██║  ██║ ██
    ██    ╚═════╝ ╚══════╝ ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝ ██
    ██                                                         ██
    ██              ██████╗ ██████╗ ████████╗                  ██
    ██             ██╔═══██╗██╔══██╗╚══██╔══╝                  ██
    ██             ██║   ██║██████╔╝   ██║                     ██
    ██             ██║   ██║██╔═══╝    ██║                     ██
    ██             ╚██████╔╝██║        ██║                     ██
    ██              ╚═════╝ ╚═╝        ╚═╝                     ██
    ██                                                         ██
    █████████████████████████████████████████████████████████████
"""

OLLAMA_OPT_COMPACT = """
    ╔════════════════════════════════════════════════════════╗
    ║  🦙  OLLAMA OPT - Local LLM Intel GPU Optimization    ║
    ╚════════════════════════════════════════════════════════╝
"""

TIER_ICONS = {
    "npu": "🚀",      # NPU - fastest tier
    "gpu": "⚡",      # GPU - fast tier
    "cpu": "🐢",      # CPU - fallback tier
    "unknown": "❓",  # Unknown
}

STATUS_INDICATORS = {
    "connected": "🟢",
    "disconnected": "🔴",
    "loading": "🟡",
    "warning": "⚠️",
    "error": "❌",
    "success": "✅",
}

# Latency bar visualization
def create_latency_bar(latency_ms, max_ms=1000, width=20):
    """Create a visual latency bar"""
    if latency_ms <= 0:
        return "[" + "─" * width + "]"
    
    percentage = min(latency_ms / max_ms, 1.0)
    filled = int(width * percentage)
    empty = width - filled
    
    # Color based on latency
    if latency_ms < 100:
        color = "green"
        symbol = "█"
    elif latency_ms < 300:
        color = "yellow"
        symbol = "█"
    elif latency_ms < 500:
        color = "orange1"
        symbol = "█"
    else:
        color = "red"
        symbol = "█"
    
    bar = "[" + symbol * filled + "·" * empty + "]"
    return f"[{color}]{bar}[/{color}] {latency_ms:6.1f}ms"

# System load visualization
def create_system_bar(percentage, width=10):
    """Create a system load bar"""
    filled = int(width * min(percentage / 100, 1.0))
    empty = width - filled
    
    if percentage < 50:
        color = "green"
    elif percentage < 75:
        color = "yellow"
    elif percentage < 90:
        color = "orange1"
    else:
        color = "red"
    
    bar = "[" + "█" * filled + "·" * empty + "]"
    return f"[{color}]{bar}[/{color}] {percentage:5.1f}%"

# Token rate visualization
def create_token_meter(tokens_per_sec, max_tokens=30):
    """Create a token throughput meter"""
    width = 15
    filled = int(width * min(tokens_per_sec / max_tokens, 1.0))
    empty = width - filled
    
    if tokens_per_sec < 5:
        color = "red"
    elif tokens_per_sec < 10:
        color = "orange1"
    elif tokens_per_sec < 20:
        color = "yellow"
    else:
        color = "green"
    
    meter = "▌" * filled + "▎" * empty
    return f"[{color}]{meter}[/{color}] {tokens_per_sec:5.1f}t/s"

# Animated spinners
SPINNERS = {
    "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
    "line": ["-", "\\", "|", "/"],
    "arrow": ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
    "dots2": ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"],
    "bounce": ["⠁", "⠂", "⠄", "⠂"],
}

def get_spinner_frame(spinner_name="dots", frame_index=0):
    """Get current spinner frame"""
    spinner = SPINNERS.get(spinner_name, SPINNERS["dots"])
    return spinner[frame_index % len(spinner)]

# Message styling decorators
MESSAGE_DECORATORS = {
    "user": {
        "prefix": "┌─ You ",
        "line": "│ ",
        "suffix": "└─",
        "color": "cyan",
        "align": "right",
    },
    "assistant": {
        "prefix": "┌─ Assistant ",
        "line": "│ ",
        "suffix": "└─",
        "color": "green",
        "align": "left",
    },
    "system": {
        "prefix": "┌─ System ",
        "line": "│ ",
        "suffix": "└─",
        "color": "yellow",
        "align": "left",
    },
    "error": {
        "prefix": "┌─ Error ",
        "line": "│ ",
        "suffix": "└─",
        "color": "red",
        "align": "left",
    },
}

# Color palette
class ColorPalette:
    PRIMARY = "cyan"
    ACCENT = "bright_cyan"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    INFO = "blue"
    SECONDARY = "magenta"
    
    METRIC_GOOD = "green"
    METRIC_FAIR = "yellow"
    METRIC_POOR = "red"
    
    TEXT_PRIMARY = "white"
    TEXT_SECONDARY = "bright_black"
    TEXT_MUTED = "dim white"

# Panel styling
PANEL_STYLE = "bright_black"
BORDER_STYLE = "cyan"

# Table styling
TABLE_HEADER_STYLE = "bold cyan"
TABLE_ROW_STYLE = "white"
TABLE_BORDER_STYLE = "bright_black"
