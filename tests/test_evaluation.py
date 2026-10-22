import math

from secure_rag.evaluation import query_metrics, unique_document_ids
from secure_rag.reranker import apply_rerank_scores
from secure_rag.schemas import SearchHit


def _hit(document_id: str, chunk_id: str) -> SearchHit:
    return SearchHit(
        document_id=document_id,
        chunk_id=chunk_id,
        title=document_id,
        content="content",
        score=1.0,
        retrieval_mode="dense",
        clearance_level="public",
        source=f"{document_id}.md",
        tenant_id="tenant",
        department="shared",
        allowed_roles=("employee",),
        clearance_rank=1,
    )


def test_metrics_are_document_level_after_chunk_deduplication() -> None:
    retrieved = unique_document_ids(
        [_hit("doc-a", "a-1"), _hit("doc-a", "a-2"), _hit("doc-b", "b-1")]
    )
    assert retrieved == ["doc-a", "doc-b"]
    assert query_metrics({"doc-b"}, retrieved) == {
        "hit_at_1": 0.0,
        "hit_at_3": 1.0,
        "recall_at_3": 1.0,
        "mrr_at_5": 0.5,
        "ndcg_at_5": 1.0 / math.log2(3),
    }


def test_rerank_preserves_rrf_score_and_orders_descending() -> None:
    hits = [_hit("doc-a", "a-1"), _hit("doc-b", "b-1")]
    ranked = apply_rerank_scores(hits, [0.2, 0.9], top_k=2)
    assert [hit.document_id for hit in ranked] == ["doc-b", "doc-a"]
    assert ranked[0].retrieval_mode == "hybrid_rerank"
    assert ranked[0].rrf_score == 1.0
    assert ranked[0].rerank_score == 0.9

