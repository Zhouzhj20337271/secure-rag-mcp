"""Authorized Dense, Sparse, and native Qdrant RRF retrieval."""

from __future__ import annotations

from .embeddings import EmbeddingModels
from .identity import assert_authorized, build_qdrant_filter
from .reranker import Reranker
from .schemas import Principal, RetrievalMode, SearchResponse
from .settings import Settings
from .store import QdrantStore


class Retriever:
    def __init__(self, settings: Settings) -> None:
        settings.ensure_runtime_dirs()
        self.settings = settings
        self.embeddings = EmbeddingModels(
            settings.dense_model, settings.sparse_model, settings.model_cache
        )
        self.store = QdrantStore(settings.db_path, settings.collection_name)
        self._reranker: Reranker | None = None

    def close(self) -> None:
        self.store.close()

    def search(
        self,
        query: str,
        principal: Principal,
        mode: RetrievalMode = "hybrid_rrf",
        top_k: int | None = None,
    ) -> SearchResponse:
        query = query.strip()
        if not query:
            raise ValueError("query must not be blank")
        limit = top_k or self.settings.top_k
        if limit <= 0 or limit > 20:
            raise ValueError("top_k must be between 1 and 20")
        query_filter = build_qdrant_filter(principal)

        if mode == "dense":
            hits = self.store.search_dense(
                self.embeddings.dense_query(query), query_filter, limit
            )
        elif mode == "sparse":
            hits = self.store.search_sparse(
                self.embeddings.sparse_query(query), query_filter, limit
            )
        elif mode in {"hybrid_rrf", "hybrid_rerank"}:
            candidate_limit = (
                self.settings.rerank_candidates if mode == "hybrid_rerank" else limit
            )
            hits = self.store.search_hybrid(
                self.embeddings.dense_query(query),
                self.embeddings.sparse_query(query),
                query_filter,
                self.settings.dense_top_k,
                self.settings.sparse_top_k,
                candidate_limit,
            )
        else:
            raise ValueError(f"Unknown retrieval mode: {mode}")

        assert_authorized(principal, hits)
        warning = None
        actual_mode = mode
        if mode == "hybrid_rerank":
            try:
                if self._reranker is None:
                    self._reranker = Reranker(
                        self.settings.rerank_model, self.settings.model_cache
                    )
                hits = self._reranker.rerank(query, hits, limit)
            # The optional model stack can raise backend-specific exceptions; any failure
            # must degrade to already-authorized RRF candidates instead of failing search.
            except Exception as exc:  # noqa: BLE001
                hits = hits[:limit]
                actual_mode = "hybrid_rrf"
                warning = f"reranker_unavailable:{type(exc).__name__}"
        assert_authorized(principal, hits)
        return SearchResponse(
            principal_id=principal.principal_id,
            query=query,
            retrieval_mode=actual_mode,
            results=tuple(hits),
            warning=warning,
        )
