"""Optional local Cross-Encoder reranking with explainable score preservation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from fastembed.rerank.cross_encoder import TextCrossEncoder

from .schemas import SearchHit


def apply_rerank_scores(
    hits: Sequence[SearchHit], scores: Sequence[float], top_k: int
) -> list[SearchHit]:
    if len(hits) != len(scores):
        raise ValueError("Rerank score count must match candidate count")
    ranked = sorted(zip(hits, scores, strict=True), key=lambda item: item[1], reverse=True)
    return [
        replace(
            hit,
            score=float(score),
            retrieval_mode="hybrid_rerank",
            rrf_score=hit.score,
            rerank_score=float(score),
        )
        for hit, score in ranked[:top_k]
    ]


class Reranker:
    def __init__(self, model_name: str, cache_dir: Path) -> None:
        self.model_name = model_name
        # The FP32 BGE model is about 1.1 GB. Disabling ONNX Runtime's CPU arena
        # avoids a second large upfront allocation on memory-constrained Windows hosts.
        self.model = TextCrossEncoder(
            model_name=model_name,
            cache_dir=str(cache_dir),
            threads=1,
            enable_cpu_mem_arena=False,
        )

    def rerank(self, query: str, hits: Sequence[SearchHit], top_k: int) -> list[SearchHit]:
        documents = [f"{hit.title}\n{hit.content}" for hit in hits]
        scores = list(self.model.rerank(query, documents))
        return apply_rerank_scores(hits, scores, top_k)
