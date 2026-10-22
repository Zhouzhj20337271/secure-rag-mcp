from pathlib import Path

from secure_rag.ingestion import parse_document, split_document, stable_point_id

ROOT = Path(__file__).resolve().parents[1]


def test_document_parsing_and_stable_chunks() -> None:
    document = parse_document(ROOT / "data/mock_docs/ops-001.md")
    first = split_document(document)
    second = split_document(document)
    assert document.document_id == "ops-001"
    assert document.clearance_rank == 2
    assert first == second
    assert first
    assert all(chunk.chunk_id.startswith("ops-001-c") for chunk in first)
    assert stable_point_id(first[0].chunk_id) == stable_point_id(first[0].chunk_id)


def test_all_fixture_documents_parse() -> None:
    paths = sorted((ROOT / "data/mock_docs").glob("*.md"))
    documents = [parse_document(path) for path in paths]
    assert len(documents) == 15
    assert len({document.document_id for document in documents}) == 15

