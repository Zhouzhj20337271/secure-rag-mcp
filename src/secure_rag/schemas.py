"""Small data contracts shared by ingestion, retrieval, MCP, and evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

RetrievalMode = Literal["dense", "sparse", "hybrid_rrf", "hybrid_rerank"]


@dataclass(frozen=True)
class Principal:
    principal_id: str
    tenant_id: str
    department: str
    roles: tuple[str, ...]
    max_clearance_rank: int


@dataclass(frozen=True)
class SourceDocument:
    document_id: str
    title: str
    tenant_id: str
    department: str
    clearance_level: str
    clearance_rank: int
    allowed_roles: tuple[str, ...]
    document_type: str
    body: str
    source: Path


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    chunk_index: int
    document: SourceDocument
    content: str

    @property
    def embedding_text(self) -> str:
        return f"{self.document.title}\n{self.content}".strip()

    def payload(self) -> dict[str, Any]:
        doc = self.document
        return {
            "document_id": doc.document_id,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "title": doc.title,
            "content": self.content,
            "tenant_id": doc.tenant_id,
            "department": doc.department,
            "clearance_level": doc.clearance_level,
            "clearance_rank": doc.clearance_rank,
            "allowed_roles": list(doc.allowed_roles),
            "document_type": doc.document_type,
            "source": doc.source.as_posix(),
        }


@dataclass(frozen=True)
class SearchHit:
    document_id: str
    chunk_id: str
    title: str
    content: str
    score: float
    retrieval_mode: RetrievalMode
    clearance_level: str
    source: str
    tenant_id: str
    department: str
    allowed_roles: tuple[str, ...]
    clearance_rank: int
    rrf_score: float | None = None
    rerank_score: float | None = None

    def public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["allowed_roles"] = list(self.allowed_roles)
        return data


@dataclass(frozen=True)
class SearchResponse:
    principal_id: str
    query: str
    retrieval_mode: RetrievalMode
    results: tuple[SearchHit, ...]
    warning: str | None = None

    def public_dict(self) -> dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "query": self.query,
            "retrieval_mode": self.retrieval_mode,
            "result_count": len(self.results),
            "results": [hit.public_dict() for hit in self.results],
            "warning": self.warning,
        }

