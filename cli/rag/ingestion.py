"""Document ingestion pipeline - reads files and normalises to plain text."""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Normalised representation of an ingested document."""

    doc_id: str
    source_path: str
    title: str
    content: str
    metadata: dict = field(default_factory=dict)


class DocumentIngester:
    """Reads files from disk and normalises them to plain-text Documents."""

    def __init__(self, supported_formats: list = None) -> None:
        self.supported_formats: list[str] = (
            supported_formats if supported_formats is not None else [".txt", ".md", ".pdf"]
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest_file(self, path) -> Optional[Document]:
        """Read a single file and return a Document, or None on any error."""
        try:
            path = Path(path)

            if not path.exists():
                logger.warning("File does not exist: %s", path)
                return None

            suffix = path.suffix.lower()
            if suffix not in self.supported_formats:
                logger.warning(
                    "Unsupported format '%s' for file: %s", suffix, path
                )
                return None

            # Build a stable doc_id from the absolute path + last-modified time.
            stat = path.stat()
            mtime = str(stat.st_mtime)
            hash_input = str(path.resolve()) + mtime
            doc_id = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

            content = self._dispatch_read(path, suffix)
            if content is None:
                return None

            metadata = {
                "format": suffix,
                "file_size_bytes": stat.st_size,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }

            return Document(
                doc_id=doc_id,
                source_path=str(path.resolve()),
                title=path.stem,
                content=content,
                metadata=metadata,
            )

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to ingest file '%s': %s", path, exc, exc_info=True)
            return None

    def ingest_directory(
        self,
        directory,
        recursive: bool = True,
    ) -> list[Document]:
        """Walk *directory* and ingest every supported file.

        Errors for individual files are logged and skipped; the rest of the
        batch is still returned.
        """
        directory = Path(directory)
        if not directory.is_dir():
            logger.error("Not a directory: %s", directory)
            return []

        documents: list[Document] = []

        if recursive:
            file_iter = directory.rglob("*")
        else:
            file_iter = directory.glob("*")

        for file_path in file_iter:
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in self.supported_formats:
                continue

            doc = self.ingest_file(file_path)
            if doc is not None:
                documents.append(doc)
            else:
                logger.debug("Skipped file during directory ingestion: %s", file_path)

        logger.info(
            "Ingested %d document(s) from directory: %s", len(documents), directory
        )
        return documents

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _dispatch_read(self, path: Path, suffix: str) -> Optional[str]:
        """Route a file to the correct reader based on its extension."""
        if suffix == ".pdf":
            return self._read_pdf(path)
        if suffix == ".md":
            return self._read_markdown(path)
        # .txt and anything else treated as plain text
        return self._read_text(path)

    def _read_text(self, path: Path) -> Optional[str]:
        """Read a plain-text file, trying common encodings."""
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
            except Exception as exc:  # noqa: BLE001
                logger.error("Error reading text file '%s': %s", path, exc)
                return None
        logger.error(
            "Could not decode text file '%s' with any attempted encoding.", path
        )
        return None

    def _read_markdown(self, path: Path) -> Optional[str]:
        """Read a Markdown file as plain text (no HTML conversion)."""
        return self._read_text(path)

    def _read_pdf(self, path: Path) -> Optional[str]:
        """Extract text from a PDF using pypdf."""
        try:
            import pypdf  # local import so missing dep doesn't break the module

            reader = pypdf.PdfReader(str(path))
            pages: list[str] = []
            for page in reader.pages:
                try:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
                except Exception as page_exc:  # noqa: BLE001
                    logger.warning(
                        "Could not extract text from a page in '%s': %s",
                        path,
                        page_exc,
                    )
            return "\n\n".join(pages) if pages else ""
        except ImportError:
            logger.error(
                "pypdf is not installed; cannot read PDF file '%s'. "
                "Install it with: pip install pypdf",
                path,
            )
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error("Error reading PDF file '%s': %s", path, exc, exc_info=True)
            return None
