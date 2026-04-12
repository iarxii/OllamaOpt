"""Probe the installed qdrant-client to discover version and available API."""
import sys

# ── Version ───────────────────────────────────────────────────────────────────
try:
    import importlib.metadata as _meta
    version = _meta.version("qdrant-client")
    print(f"qdrant-client version : {version}")
except Exception as exc:
    print(f"Could not read version : {exc}")

# ── Available top-level names ─────────────────────────────────────────────────
try:
    import qdrant_client
    print(f"\nqdrant_client.__file__ : {qdrant_client.__file__}")
except ImportError as exc:
    print(f"Cannot import qdrant_client: {exc}")
    sys.exit(1)

# ── QdrantClient method inventory ────────────────────────────────────────────
from qdrant_client import QdrantClient

public_methods = sorted(
    name for name in dir(QdrantClient)
    if not name.startswith("__")
)
print(f"\nAll public attributes/methods on QdrantClient ({len(public_methods)} total):")
for name in public_methods:
    print(f"  {name}")

# ── Search / query related methods ───────────────────────────────────────────
keywords = ("search", "query", "find", "retrieve", "nearest", "lookup")
relevant = [m for m in public_methods if any(k in m.lower() for k in keywords)]
print(f"\nSearch/query-related methods ({len(relevant)}):")
for name in relevant:
    print(f"  {name}")

# ── models / Distance / VectorParams availability ────────────────────────────
print("\n[qdrant_client.models availability]")
try:
    from qdrant_client import models as qmodels
    print(f"  qdrant_client.models : OK  ({qmodels.__file__})")
    for sym in ("Distance", "VectorParams", "PointStruct",
                "Filter", "FieldCondition", "MatchValue",
                "ScoredPoint", "SearchRequest"):
        present = hasattr(qmodels, sym)
        print(f"    {'OK  ' if present else 'MISS'} {sym}")
except ImportError as exc:
    print(f"  FAIL: {exc}")

print("\n[qdrant_client.http.models availability]")
try:
    from qdrant_client.http import models as http_models
    print(f"  qdrant_client.http.models : OK  ({http_models.__file__})")
    for sym in ("Distance", "VectorParams", "PointStruct",
                "Filter", "FieldCondition", "MatchValue"):
        present = hasattr(http_models, sym)
        print(f"    {'OK  ' if present else 'MISS'} {sym}")
except ImportError as exc:
    print(f"  FAIL: {exc}")

# ── Try to instantiate a client in memory (no disk) and call search/query ────
print("\n[Quick functional probe with in-memory client]")
import tempfile, os

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        client = QdrantClient(path=tmpdir)
        print(f"  QdrantClient(path=...) : OK")

        # Create a tiny collection
        try:
            from qdrant_client import models as qmodels
            Distance   = qmodels.Distance
            VectorParams = qmodels.VectorParams
            PointStruct  = qmodels.PointStruct
        except Exception:
            from qdrant_client.http import models as qmodels
            Distance   = qmodels.Distance
            VectorParams = qmodels.VectorParams
            PointStruct  = qmodels.PointStruct

        col = "probe_col"
        client.create_collection(
            collection_name=col,
            vectors_config=VectorParams(size=4, distance=Distance.COSINE),
        )
        print(f"  create_collection      : OK")

        # Upsert one point
        client.upsert(
            collection_name=col,
            points=[
                PointStruct(id="00000000-0000-0000-0000-000000000001",
                            vector=[0.1, 0.2, 0.3, 0.4],
                            payload={"text": "hello"})
            ],
        )
        print(f"  upsert                 : OK")

        # Try each candidate search method
        for method_name in ("search", "query", "query_points"):
            method = getattr(client, method_name, None)
            if method is None:
                print(f"  {method_name:25s}: NOT PRESENT — skipping")
                continue
            try:
                if method_name == "search":
                    hits = method(
                        collection_name=col,
                        query_vector=[0.1, 0.2, 0.3, 0.4],
                        limit=1,
                        score_threshold=0.0,
                        with_payload=True,
                    )
                elif method_name == "query":
                    hits = method(
                        collection_name=col,
                        query=[0.1, 0.2, 0.3, 0.4],
                        limit=1,
                        score_threshold=0.0,
                        with_payload=True,
                    )
                elif method_name == "query_points":
                    hits = method(
                        collection_name=col,
                        query=[0.1, 0.2, 0.3, 0.4],
                        limit=1,
                        score_threshold=0.0,
                        with_payload=True,
                    )
                print(f"  {method_name:25s}: OK  -> returned {type(hits).__name__}  len={len(hits) if hasattr(hits,'__len__') else '?'}")
                # Print the first hit so we know the shape
                if hits:
                    first = hits[0] if isinstance(hits, list) else (hits.points[0] if hasattr(hits, 'points') else hits)
                    print(f"    first hit type : {type(first).__name__}")
                    print(f"    first hit attrs: {[a for a in dir(first) if not a.startswith('_')]}")
            except Exception as exc:
                print(f"  {method_name:25s}: FAIL -> {exc}")

        # Close client before tempdir is cleaned up
        try:
            client.close()
        except Exception:
            pass

except Exception as exc:
    print(f"  Functional probe FAIL: {exc}")

print("\nProbe complete.")
