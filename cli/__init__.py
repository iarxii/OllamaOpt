"""
OllamaOpt Rich CLI - Claude/Gemini-style interface for local Ollama models
"""

from .metrics_collector import initialize_collector, get_collector, shutdown_collector
from .chat_interface import ChatInterface, CommandHandler
from .dashboard import Dashboard
from .formatters import MessageFormatter, ResponseFormatter

__version__ = "1.0.0"
__author__ = "OllamaOpt Team"

__all__ = [
    "initialize_collector",
    "get_collector",
    "shutdown_collector",
    "ChatInterface",
    "CommandHandler",
    "Dashboard",
    "MessageFormatter",
    "ResponseFormatter",
]
