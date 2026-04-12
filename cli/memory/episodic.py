"""Long-term episodic memory — tagged summaries stored and retrieved from Qdrant."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests

# Qdrant is an optional dependency — the module must still import cleanly without it.
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    _QDRANT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _QDRANT_AVAILABLE = False

logger = logging.getLogger(__name__)

_COLLECTION = "ollamaopt_memory"
_VECTOR_DIM = 768


@dataclass
class MemoryItem:
    """A single episodic memory entry."""

    memory_id: str
    content: str
    topic: str
    source: str
    created_at: str
    metadata: dict = field(default_factory=dict)


class EpisodicMemory:
    """Long-term episodic memory backed by a local Qdrant vector store.

    All Qdrant and network operations are wrapped in broad exception handlers so
    that any failure (Qdrant offline, embedding model unavailable, disk error, …)
    is silently logged and the caller receives ``None`` or an empty list instead
    of an unhandled exception.

    Parameters
    ----------
    persist_dir:
        Directory path for Qdrant's on-disk storage.
    api_base:
        Base URL for the Ollama API (used to generate embeddings).
    embedding_model:
        Name of the Ollama model used to produce 768-dim embeddings.
    """

    def __init__(
        self,
        persist_dir: str = "data/memory",
        api_base: str = "http://localhost:11434",
        embedding_model: str = "nomic-embed-text",
    ) -> None:
        self.persist_dir = persist_dir
        self.api_base = api_base.rstrip("/")
        self.embedding_model = embedding_model
        self._collection_name = _COLLECTION
        self._client: "QdrantClient | None" = None
        self._available: bool = False

        if not _QDRANT_AVAILABLE:
            logger.warning(
                "qdrant-client is not installed; EpisodicMemory will be unavailable. "
                "Install it with: pip install qdrant-client"
            )
            return

        try:
            self._client = QdrantClient(path=persist_dir)
            self._init_collection()
            self._available = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("EpisodicMemory: failed to initialise Qdrant client: %s", exc)
            self._client = None
            self._available = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the Qdrant client initialised successfully."""
        return self._available and self._client is not None

    def add_memory(
        self,
        content: str,
        topic: str = "",
        source: str = "user",
    ) -> "str | None":
        """Embed *content* and store it as a new memory item.

        Returns the UUID string of the new item on success, or ``None`` on any
        failure (Ollama offline, Qdrant error, etc.).
        """
        if not self.is_available():
            return None

        embedding = self._embed(content)
        if embedding is None:
            return None

        memory_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "content": content,
            "topic": topic,
            "source": source,
            "created_at": created_at,
            "metadata": {"topic": topic, "source": source},
        }

        try:
            self._client.upsert(  # type: ignore[union-attr]
                collection_name=self._collection_name,
                points=[
                    PointStruct(
                        id=memory_id,
                        vector=embedding,
                        payload=payload,
                    )
                ],
            )
            return memory_id
        except Exception as exc:  # noqa: BLE001
            logger.warning("EpisodicMemory.add_memory: upsert failed: %s", exc)
            return None

    def retrieve_relevant(
        self,
        query: str,
        top_k: int = 3,
        score_threshold: float = 0.4,
    ) -> "list[MemoryItem]":
        """Search for memory items semantically similar to *query*.

        Returns up to *top_k* items with a similarity score >= *score_threshold*.
        Returns an empty list on any failure.
        """
        if not self.is_available():
            return []

        embedding = self._embed(query)
        if embedding is None:
            return []

        try:
            hits = self._client.search(  # type: ignore[union-attr]
                collection_name=self._collection_name,
                query_vector=embedding,
                limit=top_k,
                score_threshold=score_threshold,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("EpisodicMemory.retrieve_relevant: search failed: %s", exc)
            return []

        items: list = []
        for hit in hits:
            payload = hit.payload or {}
            items.append(
                MemoryItem(
                    memory_id=str(hit.id),
                    content=payload.get("content", ""),
                    topic=payload.get("topic", ""),
                    source=payload.get("source", ""),
                    created_at=payload.get("created_at", ""),
                    metadata=payload.get("metadata", {}),
                )
            )
        return items

    def format_for_context(self, items: "list[MemoryItem]", max_chars: int = 400) -> str:
        """Format a list of MemoryItems into a context string.

        Each item is rendered as::

            [Memory: {topic}]
            {content}

        The combined result is hard-truncated to *max_chars*.
        """
        if not items:
            return ""

        parts: list = []
        used = 0
        for item in items:
            header = f"[Memory: {item.topic}]"
            entry = f"{header}\n{item.content}\n"
            if used + len(entry) > max_chars:
                remaining = max_chars - used
                if remaining > len(header) + 5:
                    parts.append(entry[:remaining])
                break
            parts.append(entry)
            used += len(entry)

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _embed(self, text: str) -> "list[float] | None":
        """Call the Ollama /api/embeddings endpoint and return the vector.

        Returns ``None`` on any network or API error.
        """
        try:
            response = requests.post(
                f"{self.api_base}/api/embeddings",
                json={"model": self.embedding_model, "prompt": text},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding")
            if not embedding:
                logger.warning(
                    "EpisodicMemory._embed: no 'embedding' key in response for model %r",
                    self.embedding_model,
                )
                return None
            return embedding
        except requests.exceptions.ConnectionError:
            # Ollama is offline — expected when running without the server.
            logger.debug("EpisodicMemory._embed: Ollama not reachable at %s", self.api_base)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("EpisodicMemory._embed: unexpected error: %s", exc)
            return None

    def _init_collection(self) -> None:
        """Create the Qdrant collection if it does not already exist."""
        if self._client is None:
            return
        try:
            existing = {c.name for c in self._client.get_collections().collections}
            if self._collection_name not in existing:
                self._client.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=VectorParams(
                        size=_VECTOR_DIM,
                        distance=Distance.COSINE,
                    ),
                )
                logger.debug(
                    "EpisodicMemory: created collection %r (dim=%d)",
                    self._collection_name,
                    _VECTOR_DIM,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("EpisodicMemory._init_collection: %s", exc)
