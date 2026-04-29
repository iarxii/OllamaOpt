"""Top-k retrieval with metadata filters and similarity threshold."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional, Dict

if TYPE_CHECKING:
    from .store import QdrantVectorStore
    from .embedder import OllamaEmbedder

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A single retrieved chunk with its similarity score and provenance."""

    chunk_id: str
    doc_id: str
    source_path: str
    title: str
    content: str
    score: float
    metadata: dict = field(default_factory=dict)


class Retriever:
    """Embeds a query, searches the vector store, and returns ranked results."""

    def __init__(
        self,
        store: "QdrantVectorStore",
        embedder: "OllamaEmbedder",
        top_k: int = 5,
        score_threshold: float = 0.3,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.top_k = top_k
        self.score_threshold = score_threshold

    # ------------------------------------------------------------------
    # Core retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        filter_metadata: Optional[Dict] = None,
    ) -> List[RetrievalResult]:
        """Embed *query*, search the store, and return ranked RetrievalResults.

        Returns an empty list when the embedder is unavailable or when the
        query embedding cannot be produced.
        """
        effective_top_k = top_k if top_k is not None else self.top_k
        effective_threshold = (
            score_threshold if score_threshold is not None else self.score_threshold
        )

        # The availability check is handled implicitly by embed_text call below.
        # Removing explicit is_available() call to reduce latency and avoid false negatives.

        query_embedding = self.embedder.embed_text(query)
        if query_embedding is None:
            logger.warning(
                "Retriever.retrieve: failed to embed query %r; "
                "returning empty results.",
                query,
            )
            return []

        raw_hits = self.store.search(
            query_embedding=query_embedding,
            top_k=effective_top_k,
            score_threshold=effective_threshold,
            filter_metadata=filter_metadata,
        )

        results: List[RetrievalResult] = []
        for hit in raw_hits:
            try:
                results.append(
                    RetrievalResult(
                        chunk_id=hit.get("chunk_id", ""),
                        doc_id=hit.get("doc_id", ""),
                        source_path=hit.get("source_path", ""),
                        title=hit.get("title", ""),
                        content=hit.get("content", ""),
                        score=float(hit.get("score", 0.0)),
                        metadata=hit.get("metadata", {}),
                    )
                )
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "Retriever.retrieve: could not build RetrievalResult from "
                    "hit %r: %s",
                    hit,
                    exc,
                )

        # Sort highest score first (store may already return them sorted, but
        # we guarantee the order here).
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def format_for_context(
        self,
        results: List[RetrievalResult],
        max_chars: int = 2000,
    ) -> str:
        """Render *results* as a cited-text block for LLM context injection.

        Each chunk is prefixed with ``[Source: <title> (<source_path>)]``.
        The combined string is truncated to *max_chars* characters.
        Returns an empty string when *results* is empty.
        """
        if not results:
            return ""

        parts: List[str] = []
        total_chars = 0

        for result in results:
            header = f"[Source: {result.title} ({result.source_path})]"
            block = f"{header}\n{result.content}\n\n"

            remaining = max_chars - total_chars
            if remaining <= 0:
                break

            if len(block) > remaining:
                # Truncate the content so we stay within budget.
                # Keep the header intact; truncate only the body.
                header_nl = f"{header}\n"
                body_budget = remaining - len(header_nl) - 2  # leave room for \n\n
                if body_budget > 0:
                    truncated_content = result.content[:body_budget]
                    block = f"{header_nl}{truncated_content}\n\n"
                else:
                    # Not even the header fits – stop here.
                    break

            parts.append(block)
            total_chars += len(block)

        return "".join(parts)

    def get_citations(
        self,
        results: List[RetrievalResult],
    ) -> List[Dict]:
        """Return a compact citation list for UI display or LLM footnotes.

        Each entry contains ``title``, ``source_path``, ``score``, and
        ``chunk_id``.
        """
        return [
            {
                "title": r.title,
                "source_path": r.source_path,
                "score": r.score,
                "chunk_id": r.chunk_id,
            }
            for r in results
        ]
