from pathlib import Path

from qdrant_client import QdrantClient, models

from secure_rag.identity import build_qdrant_filter, is_authorized, load_principals
from secure_rag.ingestion import parse_document

ROOT = Path(__file__).resolve().parents[1]


def test_qdrant_filter_matches_policy_oracle_for_all_120_pairs() -> None:
    principals = load_principals(ROOT / "config/principals.yaml")
    documents = [
        parse_document(path) for path in sorted((ROOT / "data/mock_docs").glob("*.md"))
    ]
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name="policy",
        vectors_config=models.VectorParams(size=1, distance=models.Distance.COSINE),
    )
    client.upsert(
        collection_name="policy",
        wait=True,
        points=[
            models.PointStruct(
                id=index,
                vector=[1.0],
                payload={
                    "document_id": document.document_id,
                    "tenant_id": document.tenant_id,
                    "department": document.department,
                    "clearance_rank": document.clearance_rank,
                    "allowed_roles": list(document.allowed_roles),
                },
            )
            for index, document in enumerate(documents)
        ],
    )

    try:
        for principal in principals.values():
            points, _ = client.scroll(
                collection_name="policy",
                scroll_filter=build_qdrant_filter(principal),
                limit=100,
                with_payload=True,
                with_vectors=False,
            )
            actual = {str(point.payload["document_id"]) for point in points}
            expected = {
                document.document_id
                for document in documents
                if is_authorized(
                    principal,
                    {
                        "tenant_id": document.tenant_id,
                        "department": document.department,
                        "clearance_rank": document.clearance_rank,
                        "allowed_roles": document.allowed_roles,
                    },
                )
            }
            assert actual == expected, principal.principal_id
    finally:
        client.close()

