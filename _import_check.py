"""Temporary import check for cli.rag package and its third-party dependencies."""
import sys
import importlib

print("=" * 60)
print("RAG Package Import Check")
print("=" * 60)

all_ok = True


def check(label, fn):
    global all_ok
    try:
        fn()
        print(f"  OK   {label}")
    except Exception as exc:
        print(f"  FAIL {label}  ->  {exc}")
        all_ok = False


# ── Third-party dependencies ──────────────────────────────────────
print("\n[Third-party packages]")
check("requests",       lambda: importlib.import_module("requests"))
check("pypdf",          lambda: importlib.import_module("pypdf"))
check("qdrant_client",  lambda: importlib.import_module("qdrant_client"))
check("rich",           lambda: importlib.import_module("rich"))
check("ollama",         lambda: importlib.import_module("ollama"))
check("pydantic",       lambda: importlib.import_module("pydantic"))

# ── Individual RAG modules ────────────────────────────────────────
print("\n[cli.rag submodules]")
check("cli.rag.ingestion  (Document, DocumentIngester)",
      lambda: __import__("cli.rag.ingestion", fromlist=["Document", "DocumentIngester"]))
check("cli.rag.chunker    (Chunk, Chunker)",
      lambda: __import__("cli.rag.chunker",   fromlist=["Chunk", "Chunker"]))
check("cli.rag.embedder   (OllamaEmbedder)",
      lambda: __import__("cli.rag.embedder",  fromlist=["OllamaEmbedder"]))
check("cli.rag.store      (QdrantVectorStore)",
      lambda: __import__("cli.rag.store",     fromlist=["QdrantVectorStore"]))
check("cli.rag.retriever  (Retriever, RetrievalResult)",
      lambda: __import__("cli.rag.retriever", fromlist=["Retriever", "RetrievalResult"]))

# ── Top-level package __init__ ────────────────────────────────────
print("\n[cli.rag public API via __init__]")


def _check_init():
    import cli.rag as rag
    required = [
        "DocumentIngester", "Document",
        "Chunker", "Chunk",
        "OllamaEmbedder",
        "QdrantVectorStore",
        "Retriever", "RetrievalResult",
    ]
    missing = [name for name in required if not hasattr(rag, name)]
    if missing:
        raise ImportError(f"Missing exports: {missing}")


check("cli.rag (all __all__ symbols present)", _check_init)

# ── Dataclass field smoke-test ────────────────────────────────────
print("\n[Dataclass field smoke-tests]")


def _check_document_fields():
    from cli.rag.ingestion import Document
    d = Document(
        doc_id="test-id",
        source_path="/tmp/test.txt",
        title="test",
        content="hello world",
        metadata={"format": ".txt"},
    )
    assert d.doc_id == "test-id"
    assert d.metadata["format"] == ".txt"


def _check_chunk_fields():
    from cli.rag.chunker import Chunk
    c = Chunk(
        chunk_id="abc_chunk_0",
        doc_id="abc",
        source_path="/tmp/test.txt",
        title="test",
        content="hello world",
        chunk_index=0,
        total_chunks=1,
        metadata={},
    )
    assert c.chunk_index == 0


def _check_retrieval_result_fields():
    from cli.rag.retriever import RetrievalResult
    r = RetrievalResult(
        chunk_id="abc_chunk_0",
        doc_id="abc",
        source_path="/tmp/test.txt",
        title="test",
        content="hello world",
        score=0.95,
        metadata={},
    )
    assert r.score == 0.95


check("Document dataclass instantiation",        _check_document_fields)
check("Chunk dataclass instantiation",           _check_chunk_fields)
check("RetrievalResult dataclass instantiation", _check_retrieval_result_fields)

# ── Chunker logic smoke-test (no network needed) ──────────────────
print("\n[Chunker logic (offline)]")


def _check_chunker_logic():
    from cli.rag.ingestion import Document
    from cli.rag.chunker import Chunker

    doc = Document(
        doc_id="smoketest",
        source_path="/tmp/smoke.txt",
        title="smoke",
        content="A" * 1024,
        metadata={"format": ".txt"},
    )
    chunker = Chunker(chunk_size=200, overlap=20, min_chunk_size=10)
    chunks = chunker.chunk_document(doc)
    assert len(chunks) > 1, "Expected multiple chunks"
    assert all(c.doc_id == "smoketest" for c in chunks)
    assert chunks[0].chunk_id == "smoketest_chunk_0"
    assert chunks[-1].total_chunks == len(chunks)


def _check_chunker_overlap():
    from cli.rag.ingestion import Document
    from cli.rag.chunker import Chunker

    text = "0123456789" * 10  # 100 chars
    doc = Document(
        doc_id="overlap-test",
        source_path="/tmp/o.txt",
        title="o",
        content=text,
        metadata={},
    )
    chunker = Chunker(chunk_size=30, overlap=10, min_chunk_size=1)
    chunks = chunker.chunk_document(doc)
    # Each consecutive pair should share the overlap characters
    for i in range(len(chunks) - 1):
        tail = chunks[i].content[-10:]
        head = chunks[i + 1].content[:10]
        assert tail == head, (
            f"Overlap mismatch at chunk {i}: tail={tail!r} head={head!r}"
        )


def _check_min_chunk_size_filter():
    from cli.rag.ingestion import Document
    from cli.rag.chunker import Chunker

    doc = Document(
        doc_id="tiny",
        source_path="/tmp/tiny.txt",
        title="tiny",
        content="Hi",          # 2 chars — below default min_chunk_size=50
        metadata={},
    )
    chunker = Chunker(chunk_size=512, overlap=64, min_chunk_size=50)
    chunks = chunker.chunk_document(doc)
    assert chunks == [], f"Expected [] for tiny content, got {chunks}"


check("Chunker.chunk_document produces correct chunks",  _check_chunker_logic)
check("Chunker sliding-window overlap correctness",      _check_chunker_overlap)
check("Chunker filters chunks below min_chunk_size",     _check_min_chunk_size_filter)

# ── OllamaEmbedder graceful offline behaviour ─────────────────────
print("\n[OllamaEmbedder (offline / graceful no-op)]")


def _check_embedder_offline():
    from cli.rag.embedder import OllamaEmbedder
    # Point at a port that is almost certainly not listening.
    emb = OllamaEmbedder(api_base="http://127.0.0.1:19999", timeout=2)
    result = emb.embed_text("hello")
    assert result is None, f"Expected None when offline, got {result!r}"
    assert emb.is_available() is False
    assert emb.get_embedding_dim() is None
    batch = emb.embed_batch(["a", "b"])
    assert batch == [None, None]


check("OllamaEmbedder returns None gracefully when Ollama is offline",
      _check_embedder_offline)

# ── QdrantVectorStore (local disk mode) ───────────────────────────
print("\n[QdrantVectorStore (local disk mode)]")


def _check_qdrant_store():
    import tempfile
    from cli.rag.store import QdrantVectorStore
    from cli.rag.chunker import Chunk

    # We manage the temp directory manually so we can close the Qdrant client
    # before the directory is deleted.  On Windows the client holds a .lock
    # file open and TemporaryDirectory.__exit__ would raise WinError 267.
    tmpdir = tempfile.mkdtemp()
    store = None
    try:
        store = QdrantVectorStore(
            collection_name="test_col",
            persist_dir=tmpdir,
            embedding_dim=4,
        )
        assert store.collection_exists(), "Collection should exist after init"

        info = store.get_collection_info()
        assert info["collection_name"] == "test_col"
        assert info["vectors_count"] == 0

        # Insert a fake chunk + embedding
        chunk = Chunk(
            chunk_id="c1_chunk_0",
            doc_id="c1",
            source_path="/tmp/x.txt",
            title="x",
            content="sample content",
            chunk_index=0,
            total_chunks=1,
            metadata={"format": ".txt"},
        )
        n = store.add_chunks([chunk], [[0.1, 0.2, 0.3, 0.4]])
        assert n == 1, f"Expected 1 upserted point, got {n}"

        hits = store.search([0.1, 0.2, 0.3, 0.4], top_k=3, score_threshold=0.0)
        assert len(hits) == 1, f"Expected 1 search hit, got {len(hits)}"
        assert hits[0]["chunk_id"] == "c1_chunk_0"
        assert hits[0]["content"] == "sample content"

        # clear_collection should reset to 0 vectors
        store.clear_collection()
        info2 = store.get_collection_info()
        assert info2["vectors_count"] == 0

    finally:
        # Always close the client before attempting directory removal so the
        # Windows .lock file is released first.
        if store is not None:
            store.close()
        import shutil
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass


check("QdrantVectorStore init, add_chunks, search, clear_collection",
      _check_qdrant_store)

# ── Retriever offline behaviour ───────────────────────────────────
print("\n[Retriever (offline embedder)]")


def _check_retriever_offline():
    import tempfile
    from cli.rag.embedder import OllamaEmbedder
    from cli.rag.store import QdrantVectorStore
    from cli.rag.retriever import Retriever

    tmpdir = tempfile.mkdtemp()
    store = None
    try:
        store = QdrantVectorStore(
            collection_name="ret_test",
            persist_dir=tmpdir,
            embedding_dim=4,
        )
        emb = OllamaEmbedder(api_base="http://127.0.0.1:19999", timeout=2)
        retriever = Retriever(store=store, embedder=emb, top_k=3)
        results = retriever.retrieve("what is the capital of France?")
        assert results == [], f"Expected [] when offline, got {results}"
    finally:
        if store is not None:
            store.close()
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def _check_format_for_context():
    from cli.rag.retriever import Retriever, RetrievalResult

    results = [
        RetrievalResult(
            chunk_id="a_chunk_0",
            doc_id="a",
            source_path="/docs/a.txt",
            title="Doc A",
            content="Alpha content here.",
            score=0.9,
            metadata={},
        ),
        RetrievalResult(
            chunk_id="b_chunk_0",
            doc_id="b",
            source_path="/docs/b.txt",
            title="Doc B",
            content="Beta content here.",
            score=0.7,
            metadata={},
        ),
    ]

    class _FakeStore:
        pass

    class _FakeEmbedder:
        pass

    retriever = Retriever(store=_FakeStore(), embedder=_FakeEmbedder())

    ctx = retriever.format_for_context(results, max_chars=2000)
    assert "[Source: Doc A (/docs/a.txt)]" in ctx, "Missing Doc A header"
    assert "Alpha content here." in ctx, "Missing Doc A content"
    assert "[Source: Doc B (/docs/b.txt)]" in ctx, "Missing Doc B header"

    # Empty results must yield an empty string
    assert retriever.format_for_context([]) == ""

    # Truncation: very small budget must honour max_chars
    ctx_small = retriever.format_for_context(results, max_chars=30)
    assert len(ctx_small) <= 30, (
        f"format_for_context exceeded max_chars: len={len(ctx_small)}"
    )

    citations = retriever.get_citations(results)
    assert len(citations) == 2
    assert citations[0]["title"] == "Doc A"
    assert citations[1]["score"] == 0.7


check("Retriever.retrieve returns [] gracefully when embedder offline",
      _check_retriever_offline)
check("Retriever.format_for_context and get_citations",
      _check_format_for_context)

# ── Summary ───────────────────────────────────────────────────────
print()
print("=" * 60)
if all_ok:
    print("ALL CHECKS PASSED")
else:
    print("ONE OR MORE CHECKS FAILED")
    sys.exit(1)
