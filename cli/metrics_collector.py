"""
Metrics collector for Ollama API and system information
Polls Ollama API endpoints and system stats in the background
"""

import threading
import time
import requests
import psutil
import subprocess
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime
import json

@dataclass
class ModelInfo:
    """Current model information"""
    name: str = "None"
    size_gb: float = 0.0
    parameters: str = "0"
    quantization: str = "Unknown"
    family: str = "Unknown"

@dataclass
class HardwareInfo:
    """Hardware detection info"""
    tier: str = "unknown"  # "npu", "gpu", "cpu"
    gpu_detected: bool = False
    npu_detected: bool = False
    cpu_model: str = "Unknown"

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    tokens_per_sec: float = 0.0
    latency_ms: float = 0.0
    last_gen_time_ms: float = 0.0

@dataclass
class SystemMetrics:
    """System resource metrics"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    vram_used_gb: float = 0.0
    vram_total_gb: float = 0.0

class MetricsCollector:
    """Background metrics collection from Ollama API and system"""

    def __init__(self, api_base: str = "http://localhost:11434"):
        self.api_base = api_base
        self.session = requests.Session()

        # Metrics state
        self.model_info = ModelInfo()
        self.hardware_info = HardwareInfo()
        self.performance = PerformanceMetrics()
        self.system = SystemMetrics()

        # Session tracking
        self.message_count = 0
        self.total_tokens_generated = 0
        self.session_start_time = datetime.now()
        self.latency_history: List[float] = []

        # Thread control
        self._stop_event = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

    def start(self):
        """Start background metrics collection"""
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(daemon=True, target=self._collect_loop)
            self._thread.start()

    def stop(self):
        """Stop background metrics collection"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _collect_loop(self):
        """Main collection loop runs in background thread"""
        hardware_checked = False
        while not self._stop_event.is_set():
            try:
                self._fetch_model_info()
                # Hardware detection is expensive (runs wmic) — only do it once
                if not hardware_checked:
                    self._fetch_hardware_info()
                    hardware_checked = True
                self._probe_latency()
                self._gather_system_metrics()

                # Poll every 2 seconds
                time.sleep(2)
            except Exception:
                pass  # Silent fail, try again next iteration

    def _fetch_model_info(self):
        """Fetch current model info from /api/tags"""
        try:
            resp = self.session.get(f"{self.api_base}/api/tags", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])

                if models:
                    # Get the first/most recent model
                    model = models[0]
                    with self._lock:
                        self.model_info.name = model.get("name", "Unknown")
                        size_bytes = model.get("size", 0)
                        self.model_info.size_gb = size_bytes / (1024**3)

                        # Extract quantization from model name
                        name_parts = self.model_info.name.split(":")
                        if len(name_parts) > 0:
                            self.model_info.family = name_parts[0]

                        model_details = model.get("details", {})
                        self.model_info.parameters = model_details.get("parameter_size", "0")
                        self.model_info.quantization = model_details.get("quantization_level", "Unknown")
        except Exception:
            pass

    def _fetch_hardware_info(self):
        """Detect hardware acceleration tier"""
        try:
            # Try to read from gpu_diagnostics output or use heuristics
            # For now, use simple heuristics

            # Check for GPU using psutil
            gpu_found = False
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                gpu_found = len(gpus) > 0
            except ImportError:
                # Fallback: check for common GPU model files
                try:
                    result = subprocess.run(
                        "wmic path win32_videocontroller get name",
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    output = result.stdout.lower()
                    gpu_found = "intel" in output or "nvidia" in output or "amd" in output
                except Exception:
                    pass

            # Get CPU model
            try:
                import platform
                cpu = platform.processor()
                if cpu:
                    with self._lock:
                        self.hardware_info.cpu_model = cpu
            except Exception:
                pass

            # Determine tier
            with self._lock:
                if gpu_found:
                    self.hardware_info.tier = "gpu"
                    self.hardware_info.gpu_detected = True
                else:
                    self.hardware_info.tier = "cpu"
        except Exception:
            pass

    def _probe_latency(self):
        """Probe API round-trip latency via a lightweight GET /api/tags ping.

        Intentionally avoids POST /api/generate so the background thread never
        triggers actual inference, which would block Ollama while the user is
        trying to chat (especially bad for thinking models like DeepSeek R1).
        Real generation latency is recorded via record_generation_latency().
        """
        try:
            start = time.time()
            resp = self.session.get(f"{self.api_base}/api/tags", timeout=3)
            latency = (time.time() - start) * 1000  # Convert to ms

            if resp.status_code == 200:
                with self._lock:
                    self.performance.latency_ms = latency
                    self.latency_history.append(latency)
                    # Keep only last 60 measurements
                    if len(self.latency_history) > 60:
                        self.latency_history = self.latency_history[-60:]
        except Exception:
            pass

    def _gather_system_metrics(self):
        """Gather CPU, memory, and VRAM metrics"""
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()

            with self._lock:
                self.system.cpu_percent = cpu
                self.system.memory_percent = mem.percent
                # VRAM estimation (total RAM * 0.7 as proxy if no dedicated GPU)
                self.system.vram_total_gb = mem.total / (1024**3)
                self.system.vram_used_gb = mem.used / (1024**3)
        except Exception:
            pass

    def get_average_latency(self) -> float:
        """Get average latency from recent measurements"""
        with self._lock:
            if self.latency_history:
                return sum(self.latency_history) / len(self.latency_history)
            return 0.0

    def get_latency_trend(self) -> str:
        """Get latency trend indicator"""
        if len(self.latency_history) < 2:
            return "→"

        recent_avg = sum(self.latency_history[-5:]) / min(5, len(self.latency_history))
        older_avg = sum(self.latency_history[:-5]) / max(1, len(self.latency_history) - 5)

        if recent_avg < older_avg * 0.9:
            return "↓"  # Improving
        elif recent_avg > older_avg * 1.1:
            return "↑"  # Degrading
        else:
            return "→"  # Stable

    def record_message(self):
        """Record that a message was sent"""
        with self._lock:
            self.message_count += 1

    def record_tokens_generated(self, count: int):
        """Record tokens generated"""
        with self._lock:
            self.total_tokens_generated += count

    def record_generation_latency(self, latency_ms: float, tokens_per_sec: float = 0.0):
        """Record latency measured from a real user generation request.

        Call this after each completed streaming response so the dashboard
        reflects actual inference speed rather than the lightweight ping.
        """
        with self._lock:
            self.performance.latency_ms = latency_ms
            if tokens_per_sec > 0:
                self.performance.tokens_per_sec = tokens_per_sec
            self.latency_history.append(latency_ms)
            if len(self.latency_history) > 60:
                self.latency_history = self.latency_history[-60:]

    def calculate_session_tokens_per_sec(self) -> float:
        """Calculate tokens/sec for entire session"""
        elapsed = (datetime.now() - self.session_start_time).total_seconds()
        if elapsed < 1:
            return 0.0
        return self.total_tokens_generated / elapsed

    def get_snapshot(self) -> Dict:
        """Get a thread-safe snapshot of all metrics"""
        with self._lock:
            return {
                "model": {
                    "name": self.model_info.name,
                    "size_gb": self.model_info.size_gb,
                    "family": self.model_info.family,
                    "quantization": self.model_info.quantization,
                },
                "hardware": {
                    "tier": self.hardware_info.tier,
                    "gpu_detected": self.hardware_info.gpu_detected,
                    "cpu_model": self.hardware_info.cpu_model,
                },
                "performance": {
                    "tokens_per_sec": self.performance.tokens_per_sec,
                    "latency_ms": self.performance.latency_ms,
                    "avg_latency_ms": self.get_average_latency(),
                    "latency_trend": self.get_latency_trend(),
                },
                "system": {
                    "cpu_percent": self.system.cpu_percent,
                    "memory_percent": self.system.memory_percent,
                    "vram_used_gb": self.system.vram_used_gb,
                    "vram_total_gb": self.system.vram_total_gb,
                    "vram_percent": (self.system.vram_used_gb / self.system.vram_total_gb * 100) if self.system.vram_total_gb > 0 else 0,
                },
                "session": {
                    "message_count": self.message_count,
                    "total_tokens": self.total_tokens_generated,
                    "tokens_per_sec": self.calculate_session_tokens_per_sec(),
                    "uptime_seconds": (datetime.now() - self.session_start_time).total_seconds(),
                },
            }

# Global metrics collector instance
_collector: Optional[MetricsCollector] = None

def get_collector() -> MetricsCollector:
    """Get or create the global metrics collector"""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector

def initialize_collector(api_base: str = "http://localhost:11434"):
    """Initialize and start the metrics collector"""
    global _collector
    _collector = MetricsCollector(api_base)
    _collector.start()
    return _collector

def shutdown_collector():
    """Shutdown the metrics collector"""
    global _collector
    if _collector:
        _collector.stop()
