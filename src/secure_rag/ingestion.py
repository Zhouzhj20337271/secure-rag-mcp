"""Parse synthetic Markdown fixtures, split them, and persist both vector branches."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import uuid
from pathlib import Path

import yaml

from .embeddings import EmbeddingModels
from .schemas import Chunk, SourceDocument
from .settings import PROJECT_ROOT, Settings
from .store import QdrantStore

CLEARANCE = {"public": 1, "internal": 2, "confidential": 3}
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", re.DOTALL)


def parse_document(path: Path) -> SourceDocument:
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"Invalid Markdown frontmatter: {path}")
    metadata = yaml.safe_load(match.group(1))
    required = {
        "document_id",
        "title",
        "tenant_id",
        "department",
        "clearance_level",
        "clearance_rank",
        "allowed_roles",
        "document_type",
    }
    missing = required - metadata.keys()
    if missing:
        raise ValueError(f"Missing metadata in {path.name}: {sorted(missing)}")
    document_id = str(metadata["document_id"])
    if path.stem != document_id:
        raise ValueError(f"Filename/document_id mismatch: {path.name}")
    clearance_level = str(metadata["clearance_level"])
    clearance_rank = int(metadata["clearance_rank"])
    if CLEARANCE.get(clearance_level) != clearance_rank:
        raise ValueError(f"Invalid clearance pair: {document_id}")
    source = path.resolve().relative_to(PROJECT_ROOT.resolve())
    return SourceDocument(
        document_id=document_id,
        title=str(metadata["title"]),
        tenant_id=str(metadata["tenant_id"]),
        department=str(metadata["department"]),
        clearance_level=clearance_level,
        clearance_rank=clearance_rank,
        allowed_roles=tuple(str(role) for role in metadata["allowed_roles"]),
        document_type=str(metadata["document_type"]),
        body=match.group(2).strip(),
        source=source,
    )


def _split_oversize(text: str, max_chars: int) -> list[str]:
    pieces: list[str] = []
    remaining = text.strip()
    while len(remaining) > max_chars:
        cut = max(
            remaining.rfind("。", 0, max_chars),
            remaining.rfind("；", 0, max_chars),
            remaining.rfind("\n", 0, max_chars),
        )
        if cut < max_chars // 2:
            cut = max_chars
        else:
            cut += 1
        pieces.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        pieces.append(remaining)
    return pieces


def split_document(document: SourceDocument, max_chars: int = 700) -> list[Chunk]:
    paragraphs: list[str] = []
    for paragraph in re.split(r"\r?\n\s*\r?\n", document.body):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        paragraphs.extend(_split_oversize(paragraph, max_chars))

    groups: list[str] = []
    current: list[str] = []
    current_size = 0
    for paragraph in paragraphs:
        separator = 2 if current else 0
        if current and current_size + separator + len(paragraph) > max_chars:
            groups.append("\n\n".join(current))
            current = []
            current_size = 0
        current.append(paragraph)
        current_size += separator + len(paragraph)
    if current:
        groups.append("\n\n".join(current))

    return [
        Chunk(
            chunk_id=f"{document.document_id}-c{index:03d}",
            chunk_index=index,
            document=document,
            content=content,
        )
        for index, content in enumerate(groups, 1)
    ]


def load_chunks(data_dir: Path) -> list[Chunk]:
    documents = [parse_document(path) for path in sorted(data_dir.glob("*.md"))]
    if not documents:
        raise ValueError(f"No Markdown documents found in {data_dir}")
    return [chunk for document in documents for chunk in split_document(document)]


def stable_point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"secure-rag-mcp:{chunk_id}"))


def validate_materials() -> None:
    command = [sys.executable, "-B", str(PROJECT_ROOT / "scripts/validate_materials.py")]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def ingest(settings: Settings, rebuild: bool = False) -> dict[str, int | str]:
    validate_materials()
    settings.ensure_runtime_dirs()
    chunks = load_chunks(settings.data_dir)
    embeddings = EmbeddingModels(
        settings.dense_model, settings.sparse_model, settings.model_cache
    )
    texts = [chunk.embedding_text for chunk in chunks]
    dense_vectors = embeddings.dense_passages(texts)
    sparse_vectors = embeddings.sparse_passages(texts)
    if not dense_vectors or len(dense_vectors) != len(sparse_vectors):
        raise RuntimeError("Dense and sparse embedding counts differ")

    store = QdrantStore(settings.db_path, settings.collection_name)
    try:
        store.ensure_collection(len(dense_vectors[0]), rebuild=rebuild)
        store.upsert_chunks(chunks, dense_vectors, sparse_vectors, stable_point_id)
        count = store.count()
    finally:
        store.close()
    return {
        "documents": len({chunk.document.document_id for chunk in chunks}),
        "chunks": len(chunks),
        "stored_points": count,
        "collection": settings.collection_name,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the synthetic SecureRAG corpus")
    parser.add_argument("--rebuild", action="store_true", help="Recreate the collection")
    args = parser.parse_args()
    result = ingest(Settings.from_env(), rebuild=args.rebuild)
    print(yaml.safe_dump(result, allow_unicode=True, sort_keys=False).strip())


if __name__ == "__main__":
    main()

