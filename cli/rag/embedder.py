"""Embedding generation via Ollama API - no sentence-transformers dependency."""

from __future__ import annotations

import logging
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)


class OllamaEmbedder:
    """Generates embeddings by calling the Ollama HTTP API.

    No sentence-transformers or local model weights are required.
    Falls back gracefully when Ollama is not running.
    """

    def __init__(
        self,
        api_base: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        timeout: int = 30,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._endpoint = f"{self.api_base}/api/embeddings"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def embed_text(self, text: str) -> Optional[List[float]]:
        """Embed a single string via the Ollama /api/embeddings endpoint.

        Returns a list of floats on success, or None on any failure.
        """
        if not text or not text.strip():
            logger.warning("embed_text received empty text; returning None.")
            return None

        payload = {"model": self.model, "prompt": text}
        try:
            response = requests.post(
                self._endpoint,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding")
            if embedding is None:
                logger.error(
                    "Ollama response missing 'embedding' key. Response: %s",
                    data,
                )
                return None
            return [float(v) for v in embedding]
        except requests.exceptions.ConnectionError:
            logger.warning(
                "Cannot connect to Ollama at %s. Is the server running?",
                self.api_base,
            )
            return None
        except requests.exceptions.Timeout:
            logger.warning(
                "Ollama embedding request timed out after %d seconds.",
                self.timeout,
            )
            return None
        except requests.exceptions.HTTPError as exc:
            logger.error("Ollama HTTP error: %s", exc)
            return None
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Unexpected error during embedding: %s", exc)
            return None

    def embed_batch(
        self, texts: List[str]
    ) -> List[Optional[List[float]]]:
        """Embed a list of strings, one at a time (Ollama has no batch endpoint).

        Displays a Rich progress bar when the ``rich`` package is available.
        Returns a list of the same length as *texts*; failed items are None.
        """
        results: List[Optional[List[float]]] = []

        # Try to show a Rich progress bar; silently skip if rich is absent.
        try:
            from rich.progress import (
                Progress,
                SpinnerColumn,
                BarColumn,
                TextColumn,
                TimeElapsedColumn,
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Embedding with {self.model}…", total=len(texts)
                )
                for text in texts:
                    results.append(self.embed_text(text))
                    progress.advance(task)
        except ImportError:
            for text in texts:
                results.append(self.embed_text(text))

        return results

    def get_embedding_dim(self) -> Optional[int]:
        """Return the dimensionality of the embedding model.

        Embeds the word "test" and returns the length of the resulting
        vector, or None if Ollama is unreachable or the call fails.
        """
        embedding = self.embed_text("test")
        if embedding is None:
            return None
        return len(embedding)

    def is_available(self) -> bool:
        """Return True if Ollama is reachable and can produce embeddings."""
        return self.get_embedding_dim() is not None
