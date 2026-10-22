"""Environment-backed project settings with project-relative paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _path_from_env(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else PROJECT_ROOT / value


def _int_from_env(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _bool_from_env(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    db_path: Path
    model_cache: Path
    principals_path: Path
    principal_id: str
    dense_model: str
    sparse_model: str
    collection_name: str
    dense_top_k: int
    sparse_top_k: int
    top_k: int
    rerank_enabled: bool
    rerank_model: str
    rerank_candidates: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            data_dir=_path_from_env("SECURERAG_DATA_DIR", "data/mock_docs"),
            db_path=_path_from_env("SECURERAG_DB_PATH", "var/qdrant"),
            model_cache=_path_from_env("SECURERAG_MODEL_CACHE", "var/models"),
            principals_path=_path_from_env(
                "SECURERAG_PRINCIPALS_PATH", "config/principals.yaml"
            ),
            principal_id=os.getenv("SECURERAG_PRINCIPAL_ID", "engineer-demo"),
            dense_model=os.getenv(
                "SECURERAG_DENSE_MODEL", "BAAI/bge-small-zh-v1.5"
            ),
            sparse_model=os.getenv("SECURERAG_SPARSE_MODEL", "Qdrant/bm25"),
            collection_name=os.getenv("SECURERAG_COLLECTION", "secure_rag_chunks"),
            dense_top_k=_int_from_env("SECURERAG_DENSE_TOP_K", 15),
            sparse_top_k=_int_from_env("SECURERAG_SPARSE_TOP_K", 15),
            top_k=_int_from_env("SECURERAG_TOP_K", 5),
            rerank_enabled=_bool_from_env("SECURERAG_RERANK_ENABLED", False),
            rerank_model=os.getenv(
                "SECURERAG_RERANK_MODEL", "BAAI/bge-reranker-base"
            ),
            rerank_candidates=_int_from_env("SECURERAG_RERANK_CANDIDATES", 15),
        )

    def ensure_runtime_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.model_cache.mkdir(parents=True, exist_ok=True)

