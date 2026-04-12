"""Probe query_points() filter parameter name in qdrant-client 1.17.1."""
import tempfile, sys

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

col = "filter_probe"

with tempfile.TemporaryDirectory() as tmpdir:
    client = QdrantClient(path=tmpdir)

    client.create_collection(
        collection_name=col,
        vectors_config=VectorParams(size=4, distance=Distance.COSINE),
    )

    client.upsert(
        collection_name=col,
        points=[
            PointStruct(
                id="00000000-0000-0000-0000-000000000001",
                vector=[0.1, 0.2, 0.3, 0.4],
                payload={"doc_id": "doc1", "label": "alpha"},
            ),
            PointStruct(
                id="00000000-0000-0000-0000-000000000002",
                vector=[0.5, 0.6, 0.7, 0.8],
                payload={"doc_id": "doc2", "label": "beta"},
            ),
        ],
    )
    print("Upserted 2 points.")

    qdrant_filter = Filter(
        must=[FieldCondition(key="label", match=MatchValue(value="alpha"))]
    )

    # Try 'query_filter' first
    for param_name in ("query_filter", "filter"):
        try:
            kwargs = dict(
                collection_name=col,
                query=[0.1, 0.2, 0.3, 0.4],
                limit=5,
                score_threshold=0.0,
                with_payload=True,
            )
            kwargs[param_name] = qdrant_filter
            response = client.query_points(**kwargs)
            points = response.points if hasattr(response, "points") else response
            print(f"  query_points(... {param_name}=Filter(...)) -> OK, {len(points)} hit(s)")
            for p in points:
                print(f"    id={p.id}  score={p.score:.4f}  payload={p.payload}")
            break
        except TypeError as exc:
            print(f"  query_points(... {param_name}=...) -> TypeError: {exc}")
        except Exception as exc:
            print(f"  query_points(... {param_name}=...) -> {type(exc).__name__}: {exc}")

    # Also probe unfiltered to confirm baseline
    print("\n  Unfiltered query_points baseline:")
    resp = client.query_points(
        collection_name=col,
        query=[0.1, 0.2, 0.3, 0.4],
        limit=5,
        score_threshold=0.0,
        with_payload=True,
    )
    pts = resp.points if hasattr(resp, "points") else resp
    for p in pts:
        print(f"    id={p.id}  score={p.score:.4f}  payload={p.payload}")

    # Inspect QueryResponse structure
    print(f"\n  QueryResponse type : {type(resp).__name__}")
    print(f"  QueryResponse attrs: {[a for a in dir(resp) if not a.startswith('_')]}")

    # Close before temp dir is deleted (Windows .lock file workaround)
    try:
        client.close()
        print("\n  client.close() : OK")
    except Exception as exc:
        print(f"\n  client.close() failed: {exc}")

print("\nProbe complete.")
