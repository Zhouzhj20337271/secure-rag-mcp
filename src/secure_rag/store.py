"""Qdrant Local storage and retrieval operations."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from qdrant_client import QdrantClient, models

from .schemas import Chunk, RetrievalMode, SearchHit


class QdrantStore:
    def __init__(self, path: Path | str, collection_name: str) -> None:
        self.path = path
        self.collection_name = collection_name
        self.client = QdrantClient(path=str(path))

    def close(self) -> None:
        self.client.close()

    def ensure_collection(self, dense_size: int, rebuild: bool = False) -> None:
        exists = self.client.collection_exists(self.collection_name)
        if exists and rebuild:
            self.client.delete_collection(self.collection_name)
            exists = False
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": models.VectorParams(
                        size=dense_size, distance=models.Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )

    def upsert_chunks(
        self,
        chunks: Sequence[Chunk],
        dense_vectors: Sequence[list[float]],
        sparse_vectors: Sequence[models.SparseVector],
        point_id: Callable[[str], str],
    ) -> None:
        if not (len(chunks) == len(dense_vectors) == len(sparse_vectors)):
            raise ValueError("Chunk and embedding counts must match")
        points = [
            models.PointStruct(
                id=point_id(chunk.chunk_id),
                vector={"dense": dense, "sparse": sparse},
                payload=chunk.payload(),
            )
            for chunk, dense, sparse in zip(chunks, dense_vectors, sparse_vectors, strict=True)
        ]
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )

    def count(self) -> int:
        return int(
            self.client.count(collection_name=self.collection_name, exact=True).count
        )

    def search_dense(
        self,
        vector: list[float],
        query_filter: models.Filter,
        limit: int,
    ) -> list[SearchHit]:
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            using="dense",
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return self._hits(result.points, "dense")

    def search_sparse(
        self,
        vector: models.SparseVector,
        query_filter: models.Filter,
        limit: int,
    ) -> list[SearchHit]:
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            using="sparse",
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return self._hits(result.points, "sparse")

    def search_hybrid(
        self,
        dense_vector: list[float],
        sparse_vector: models.SparseVector,
        query_filter: models.Filter,
        dense_limit: int,
        sparse_limit: int,
        final_limit: int,
    ) -> list[SearchHit]:
        result = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_vector,
                    using="dense",
                    filter=query_filter,
                    limit=dense_limit,
                ),
                models.Prefetch(
                    query=sparse_vector,
                    using="sparse",
                    filter=query_filter,
                    limit=sparse_limit,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=final_limit,
            with_payload=True,
            with_vectors=False,
        )
        return self._hits(result.points, "hybrid_rrf")

    @staticmethod
    def _hits(points: Sequence[models.ScoredPoint], mode: RetrievalMode) -> list[SearchHit]:
        hits: list[SearchHit] = []
        for point in points:
            payload = point.payload or {}
            hits.append(
                SearchHit(
                    document_id=str(payload["document_id"]),
                    chunk_id=str(payload["chunk_id"]),
                    title=str(payload["title"]),
                    content=str(payload["content"]),
                    score=float(point.score),
                    retrieval_mode=mode,
                    clearance_level=str(payload["clearance_level"]),
                    source=str(payload["source"]),
                    tenant_id=str(payload["tenant_id"]),
                    department=str(payload["department"]),
                    allowed_roles=tuple(str(role) for role in payload["allowed_roles"]),
                    clearance_rank=int(payload["clearance_rank"]),
                )
            )
        return hits

