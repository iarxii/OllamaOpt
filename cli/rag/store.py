"""Qdrant local vector store - persists to disk, no separate server needed."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency guard — importing this module must never crash even when
# qdrant-client is absent.
# ---------------------------------------------------------------------------
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        VectorParams,
    )
    from qdrant_client.http.exceptions import UnexpectedResponse

    _QDRANT_AVAILABLE = True
except ImportError:
    _QDRANT_AVAILABLE = False
    logger.warning(
        "qdrant-client is not installed. "
        "QdrantVectorStore will be non-functional. "
        "Install it with: pip install qdrant-client"
    )

# Local import — guarded to avoid circular issues at import time.
try:
    from .chunker import Chunk
except ImportError:
    Chunk = Any  # type: ignore


class QdrantVectorStore:
    """
    Local Qdrant vector store backed by disk persistence.

    Uses ``QdrantClient(path=...)`` so no separate Qdrant server process is
    required.  The collection is created automatically on first use.

    Compatible with qdrant-client >= 1.7 (uses ``query_points`` instead of
    the removed ``search`` method).
    """

    def __init__(
        self,
        collection_name: str = "ollamaopt_docs",
        persist_dir: str = "data/qdrant",
        embedding_dim: int = 768,
    ) -> None:
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self.embedding_dim = embedding_dim
        self._client: Optional["QdrantClient"] = None

        if not _QDRANT_AVAILABLE:
            logger.error(
                "qdrant-client is not installed. "
                "Install it with: pip install qdrant-client"
            )
            return

        # Ensure persistence directory exists.
        try:
            Path(persist_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error(
                "Failed to create Qdrant persist directory %r: %s",
                persist_dir,
                exc,
            )
            return

        # Initialise local client.
        try:
            self._client = QdrantClient(path=persist_dir)
            logger.debug("QdrantClient initialised at path %r", persist_dir)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to initialise QdrantClient: %s", exc)
            return

        # Ensure the collection exists on startup.
        self._ensure_collection()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_collection(self) -> None:
        """Create the target collection if it does not already exist."""
        if self._client is None:
            return
        try:
            existing_names = [
                c.name for c in self._client.get_collections().collections
            ]
            if self.collection_name not in existing_names:
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(
                    "Created Qdrant collection %r (dim=%d, distance=COSINE)",
                    self.collection_name,
                    self.embedding_dim,
                )
            else:
                logger.debug("Collection %r already exists.", self.collection_name)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Error ensuring collection %r: %s", self.collection_name, exc
            )

    def _build_filter(
        self, filter_metadata: Optional[Dict[str, Any]]
    ) -> Optional["Filter"]:
        """Convert a plain ``{key: value}`` dict into a Qdrant ``Filter``."""
        if not filter_metadata:
            return None
        try:
            conditions = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in filter_metadata.items()
            ]
            return Filter(must=conditions) if conditions else None
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not build Qdrant filter from %r: %s", filter_metadata, exc
            )
            return None

    @staticmethod
    def _stable_point_id(chunk_id: str) -> str:
        """Return a deterministic UUID string derived from *chunk_id*."""
        return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Release the Qdrant client and its file-system lock.

        Call this when the store is no longer needed, especially on Windows
        where the ``.lock`` file held by the client prevents directory removal
        while the client is alive.
        """
        if self._client is not None:
            try:
                self._client.close()
                logger.debug("QdrantClient closed.")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error closing QdrantClient: %s", exc)
            finally:
                self._client = None

    def collection_exists(self) -> bool:
        """Return ``True`` if the managed collection exists in Qdrant."""
        if self._client is None:
            return False
        try:
            existing_names = [
                c.name for c in self._client.get_collections().collections
            ]
            return self.collection_name in existing_names
        except Exception as exc:  # noqa: BLE001
            logger.warning("collection_exists check failed: %s", exc)
            return False

    def add_chunks(
        self,
        chunks: List["Chunk"],
        embeddings: List[Optional[List[float]]],
    ) -> int:
        """Upsert chunk embeddings into the Qdrant collection.

        Parameters
        ----------
        chunks:
            List of ``Chunk`` objects to store.
        embeddings:
            Parallel list of embedding vectors.  ``None`` entries are skipped.

        Returns
        -------
        int
            Number of points successfully upserted.
        """
        if self._client is None:
            logger.warning("add_chunks called but QdrantClient is not available.")
            return 0

        points: List["PointStruct"] = []
        skipped = 0

        for chunk, embedding in zip(chunks, embeddings):
            if embedding is None:
                logger.debug(
                    "Skipping chunk %r — embedding is None.", chunk.chunk_id
                )
                skipped += 1
                continue

            payload: Dict[str, Any] = {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "source_path": chunk.source_path,
                "title": chunk.title,
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "metadata": chunk.metadata,
            }

            points.append(
                PointStruct(
                    id=self._stable_point_id(chunk.chunk_id),
                    vector=embedding,
                    payload=payload,
                )
            )

        if not points:
            logger.info("No valid points to upsert (skipped=%d).", skipped)
            return 0

        try:
            self._client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
            logger.info(
                "Upserted %d point(s) to collection %r (skipped=%d).",
                len(points),
                self.collection_name,
                skipped,
            )
            return len(points)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to upsert points: %s", exc)
            return 0

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: float = 0.3,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform a nearest-neighbour search using ``query_points``.

        Parameters
        ----------
        query_embedding:
            Dense query vector (must match the collection's dimension).
        top_k:
            Maximum number of results to return.
        score_threshold:
            Minimum cosine similarity score; lower-scoring hits are dropped.
        filter_metadata:
            Optional ``{key: value}`` pairs to pre-filter results by payload
            fields before ranking.

        Returns
        -------
        list[dict]
            Each dict contains: ``chunk_id``, ``doc_id``, ``source_path``,
            ``title``, ``content``, ``score``, ``metadata``.
        """
        if self._client is None:
            logger.warning("search called but QdrantClient is not available.")
            return []

        qdrant_filter = self._build_filter(filter_metadata)

        try:
            # qdrant-client >= 1.7 removed client.search(); use query_points().
            response = self._client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=qdrant_filter,
                with_payload=True,
            )
            # query_points returns a QueryResponse; the hits live in .points.
            hits = response.points if hasattr(response, "points") else list(response)
        except Exception as exc:  # noqa: BLE001
            logger.error("Qdrant query_points failed: %s", exc)
            return []

        results: List[Dict[str, Any]] = []
        for hit in hits:
            payload: Dict[str, Any] = hit.payload or {}
            results.append(
                {
                    "chunk_id": payload.get("chunk_id", ""),
                    "doc_id": payload.get("doc_id", ""),
                    "source_path": payload.get("source_path", ""),
                    "title": payload.get("title", ""),
                    "content": payload.get("content", ""),
                    "score": float(hit.score),
                    "metadata": payload.get("metadata", {}),
                }
            )

        logger.debug(
            "search returned %d result(s) (top_k=%d, threshold=%.2f).",
            len(results),
            top_k,
            score_threshold,
        )
        return results

    def get_collection_info(self) -> Dict[str, Any]:
        """Return basic statistics about the collection.

        Returns
        -------
        dict
            Keys: ``vectors_count``, ``collection_name``, ``status``.
        """
        if self._client is None:
            return {
                "vectors_count": 0,
                "collection_name": self.collection_name,
                "status": "unavailable",
            }
        try:
            info = self._client.get_collection(self.collection_name)
            vectors_count = (
                info.vectors_count
                if hasattr(info, "vectors_count") and info.vectors_count is not None
                else 0
            )
            status = str(info.status) if hasattr(info, "status") else "unknown"
            return {
                "vectors_count": vectors_count,
                "collection_name": self.collection_name,
                "status": status,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_collection_info failed: %s", exc)
            return {
                "vectors_count": 0,
                "collection_name": self.collection_name,
                "status": "error",
            }

    def clear_collection(self) -> None:
        """Delete and recreate the collection, removing all stored vectors."""
        if self._client is None:
            logger.warning(
                "clear_collection called but QdrantClient is not available."
            )
            return
        try:
            if self.collection_exists():
                self._client.delete_collection(self.collection_name)
                logger.info("Deleted collection %r.", self.collection_name)
            self._ensure_collection()
            logger.info("Collection %r recreated.", self.collection_name)
        except Exception as exc:  # noqa: BLE001
            logger.error("clear_collection failed: %s", exc)
