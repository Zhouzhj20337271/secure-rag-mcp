"""FastEmbed model loading and dense/sparse vector conversion."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import models


class EmbeddingModels:
    def __init__(self, dense_model: str, sparse_model: str, cache_dir: Path) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.dense_model_name = dense_model
        self.sparse_model_name = sparse_model
        self.dense = TextEmbedding(model_name=dense_model, cache_dir=str(cache_dir))
        self.sparse = SparseTextEmbedding(model_name=sparse_model, cache_dir=str(cache_dir))

    def dense_passages(self, texts: Iterable[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self.dense.passage_embed(list(texts))]

    def dense_query(self, query: str) -> list[float]:
        return next(iter(self.dense.query_embed(query))).tolist()

    def sparse_passages(self, texts: Iterable[str]) -> list[models.SparseVector]:
        return [self._to_qdrant(vector) for vector in self.sparse.passage_embed(list(texts))]

    def sparse_query(self, query: str) -> models.SparseVector:
        return self._to_qdrant(next(iter(self.sparse.query_embed(query))))

    @staticmethod
    def _to_qdrant(vector: object) -> models.SparseVector:
        indices = vector.indices
        values = vector.values
        return models.SparseVector(indices=indices.tolist(), values=values.tolist())

