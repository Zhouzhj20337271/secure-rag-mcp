from qdrant_client import models

from secure_rag.identity import build_qdrant_filter
from secure_rag.schemas import Principal
from secure_rag.store import QdrantStore


def test_hybrid_prefetch_filters_before_fusion() -> None:
    store = QdrantStore(":memory:", "hybrid")
    store.ensure_collection(dense_size=2)
    store.client.upsert(
        collection_name="hybrid",
        wait=True,
        points=[
            models.PointStruct(
                id=1,
                vector={
                    "dense": [1.0, 0.0],
                    "sparse": models.SparseVector(indices=[1], values=[1.0]),
                },
                payload={
                    "document_id": "allowed",
                    "chunk_id": "allowed-c001",
                    "title": "allowed",
                    "content": "allowed",
                    "tenant_id": "tenant-a",
                    "department": "engineering",
                    "clearance_level": "internal",
                    "clearance_rank": 2,
                    "allowed_roles": ["engineer"],
                    "source": "allowed.md",
                },
            ),
            models.PointStruct(
                id=2,
                vector={
                    "dense": [1.0, 0.0],
                    "sparse": models.SparseVector(indices=[1], values=[1.0]),
                },
                payload={
                    "document_id": "forbidden",
                    "chunk_id": "forbidden-c001",
                    "title": "forbidden",
                    "content": "secret",
                    "tenant_id": "tenant-a",
                    "department": "engineering",
                    "clearance_level": "confidential",
                    "clearance_rank": 3,
                    "allowed_roles": ["engineer"],
                    "source": "forbidden.md",
                },
            ),
        ],
    )
    principal = Principal(
        principal_id="engineer",
        tenant_id="tenant-a",
        department="engineering",
        roles=("engineer",),
        max_clearance_rank=2,
    )
    try:
        hits = store.search_hybrid(
            dense_vector=[1.0, 0.0],
            sparse_vector=models.SparseVector(indices=[1], values=[1.0]),
            query_filter=build_qdrant_filter(principal),
            dense_limit=10,
            sparse_limit=10,
            final_limit=10,
        )
        assert [hit.document_id for hit in hits] == ["allowed"]
        assert all("secret" not in hit.content for hit in hits)
    finally:
        store.close()
