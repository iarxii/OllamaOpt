"""Text chunker with sliding window and metadata preservation."""

import hashlib
import logging
from dataclasses import dataclass, field
from typing import List

from .ingestion import Document

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A single chunk of text derived from a Document."""

    chunk_id: str
    doc_id: str
    source_path: str
    title: str
    content: str
    chunk_index: int
    total_chunks: int
    metadata: dict = field(default_factory=dict)


class Chunker:
    """Splits documents into overlapping fixed-size character chunks."""

    def __init__(
        self,
        chunk_size: int = 512,
        overlap: int = 64,
        min_chunk_size: int = 50,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer.")
        if overlap < 0:
            raise ValueError("overlap must be non-negative.")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size.")
        if min_chunk_size < 0:
            raise ValueError("min_chunk_size must be non-negative.")

        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk_document(self, doc: Document) -> List[Chunk]:
        """Split a single Document into a list of Chunks.

        Chunks are created with a sliding window of *chunk_size* characters
        and *overlap* characters of context carried over from the previous
        window.  Chunks whose stripped length is below *min_chunk_size* are
        discarded.

        Args:
            doc: The Document to split.

        Returns:
            An ordered list of Chunk objects (may be empty if content is
            too short or blank).
        """
        if not doc or not doc.content:
            logger.debug(
                "chunk_document: document '%s' has no content — skipping.",
                getattr(doc, "doc_id", "<unknown>"),
            )
            return []

        raw_windows = self._sliding_windows(doc.content)

        # First pass: strip and filter below min_chunk_size
        valid_windows: List[str] = []
        for window in raw_windows:
            stripped = window.strip()
            if len(stripped) >= self.min_chunk_size:
                valid_windows.append(stripped)

        total = len(valid_windows)
        if total == 0:
            logger.debug(
                "chunk_document: all windows for '%s' were below min_chunk_size (%d) "
                "— no chunks produced.",
                doc.doc_id,
                self.min_chunk_size,
            )
            return []

        chunks: List[Chunk] = []
        for i, window_text in enumerate(valid_windows):
            chunk_id = self._make_chunk_id(doc.doc_id, i)

            # Copy document-level metadata and enrich with chunk positional info.
            chunk_metadata = dict(doc.metadata) if doc.metadata else {}
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = total

            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=doc.doc_id,
                source_path=doc.source_path,
                title=doc.title,
                content=window_text,
                chunk_index=i,
                total_chunks=total,
                metadata=chunk_metadata,
            )
            chunks.append(chunk)

        logger.debug(
            "chunk_document: produced %d chunk(s) from document '%s'.",
            len(chunks),
            doc.doc_id,
        )
        return chunks

    def chunk_documents(self, docs: List[Document]) -> List[Chunk]:
        """Chunk a list of Documents and return a flat list of all Chunks.

        Args:
            docs: Iterable of Document objects.

        Returns:
            A flat, ordered list of all Chunk objects across all documents.
        """
        all_chunks: List[Chunk] = []
        for doc in docs:
            try:
                chunks = self.chunk_document(doc)
                all_chunks.extend(chunks)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "chunk_documents: unexpected error while chunking document '%s': %s",
                    getattr(doc, "doc_id", "<unknown>"),
                    exc,
                )
        return all_chunks

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _sliding_windows(self, text: str) -> List[str]:
        """Generate raw character-level sliding windows over *text*.

        The step size between window starts is ``chunk_size - overlap``.
        The last window is always anchored at the end of the text so that
        no content is lost, even if the final step does not land exactly
        on a multiple of the step size.

        Args:
            text: Source text to slice.

        Returns:
            List of raw (un-stripped) text windows.
        """
        step = self.chunk_size - self.overlap
        text_len = len(text)
        windows: List[str] = []

        start = 0
        while start < text_len:
            end = start + self.chunk_size
            window = text[start:end]
            windows.append(window)
            if end >= text_len:
                break
            start += step

        return windows

    @staticmethod
    def _make_chunk_id(doc_id: str, index: int) -> str:
        """Produce a deterministic chunk identifier.

        Format: ``{doc_id}_chunk_{index}``.  The doc_id is kept verbatim so
        that the relationship to the parent document is immediately obvious.
        A short sha256 prefix is used instead when doc_id exceeds 60 chars
        to keep IDs manageable.

        Args:
            doc_id: The parent document's identifier.
            index:  Zero-based index of this chunk within the document.

        Returns:
            A string chunk identifier.
        """
        if len(doc_id) > 60:
            short = hashlib.sha256(doc_id.encode()).hexdigest()[:12]
            return f"{short}_chunk_{index}"
        return f"{doc_id}_chunk_{index}"
