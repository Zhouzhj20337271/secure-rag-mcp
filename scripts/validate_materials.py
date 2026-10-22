"""Validate preparation fixtures only; this is not a retrieval/security test.

Run from any directory: python -B scripts/validate_materials.py
Requires PyYAML. Compatible with Python 3.9 for pre-environment validation.
"""

import json
import re
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLEARANCE = {"public": 1, "internal": 2, "confidential": 3}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def authorized(principal, document):
    """Fixture oracle; the future application's filter must be tested separately."""
    return (
        principal["tenant_id"] == document["tenant_id"]
        and principal["max_clearance_rank"] >= document["clearance_rank"]
        and document["department"] in (principal["department"], "shared")
        and bool(set(principal["roles"]) & set(document["allowed_roles"]))
    )


def main():
    principal_config = yaml.safe_load(
        (ROOT / "config/principals.yaml").read_text(encoding="utf-8")
    )
    principals = principal_config["principals"]
    require(len(principals) == 8, "Expected 8 demo/test principals")
    for name, principal in principals.items():
        require(principal["max_clearance_rank"] in (1, 2, 3), name)
        require(isinstance(principal["roles"], list) and principal["roles"], name)
        require("employee" in principal["roles"], name)
        require(principal.get("tenant_id") and principal.get("department"), name)

    documents = {}
    required = {
        "document_id", "title", "tenant_id", "department", "clearance_level",
        "clearance_rank", "allowed_roles", "document_type",
    }
    for path in sorted((ROOT / "data/mock_docs").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", text, re.DOTALL)
        require(match is not None, f"Invalid frontmatter: {path.name}")
        document = yaml.safe_load(match.group(1))
        require(required <= document.keys(), f"Missing metadata: {path.name}")
        doc_id = document["document_id"]
        require(doc_id not in documents, f"Duplicate document ID: {doc_id}")
        require(path.stem == doc_id, f"Filename/ID mismatch: {path.name}")
        require(
            CLEARANCE.get(document["clearance_level"]) == document["clearance_rank"],
            f"Invalid clearance: {doc_id}",
        )
        require(
            isinstance(document["allowed_roles"], list) and document["allowed_roles"],
            f"No allowed roles: {doc_id}",
        )
        require("虚构企业演示数据" in match.group(2), f"Missing synthetic label: {doc_id}")
        document["body"] = match.group(2)
        documents[doc_id] = document

    require(len(documents) == 15, "Expected 15 documents")
    require(len({d["tenant_id"] for d in documents.values()}) == 2, "Expected two tenants")
    require(
        {d["clearance_rank"] for d in documents.values()} == {1, 2, 3},
        "Expected all three clearances",
    )
    matrix = {
        name: {doc_id for doc_id, doc in documents.items() if authorized(principal, doc)}
        for name, principal in principals.items()
    }
    expected_sizes = {
        "intern-demo": 3, "engineer-demo": 9, "hr-demo": 4,
        "finance-demo": 4, "finance-manager-demo": 5, "executive-demo": 4,
        "finance-role-probe-demo": 4, "other-engineer-demo": 2,
    }
    require(
        {name: len(ids) for name, ids in matrix.items()} == expected_sizes,
        "Authorization fixture matrix changed; review it explicitly",
    )
    for doc_id in documents:
        require(any(doc_id in ids for ids in matrix.values()), f"Unreachable: {doc_id}")
    require("public-001" not in matrix["other-engineer-demo"], "Cross-tenant public access")
    require("boreal-public-001" not in matrix["intern-demo"], "Cross-tenant public access")
    require("finance-002" not in matrix["finance-role-probe-demo"], "Role boundary missing")
    require("finance-002" in matrix["finance-manager-demo"], "Manager positive case missing")

    queries = []
    for number, line in enumerate(
        (ROOT / "data/benchmark.jsonl").read_text(encoding="utf-8").splitlines(), 1
    ):
        require(bool(line.strip()), f"Blank benchmark line {number}")
        queries.append(json.loads(line))
    require(len(queries) == 48, "Expected 48 benchmark queries")
    require(len({q["id"] for q in queries}) == 48, "Duplicate query IDs")
    require(
        Counter(q["category"] for q in queries)
        == {
            "exact": 6,
            "semantic": 8,
            "ordinary": 4,
            "hard": 12,
            "comparison": 6,
            "security": 12,
        },
        "Unexpected category counts",
    )
    require(
        Counter(q["split"] for q in queries)
        == {"dev": 18, "test": 18, "security": 12},
        "Unexpected split counts",
    )
    for query in queries:
        query_id = query["id"]
        require(query["principal_id"] in principals, f"Unknown principal: {query_id}")
        require(query["query"].strip() and query["reference_answer"].strip(), query_id)
        relevant = set(query["relevant_document_ids"])
        forbidden = set(query.get("forbidden_document_ids", []))
        require(relevant | forbidden <= documents.keys(), f"Unknown doc label: {query_id}")
        allowed = matrix[query["principal_id"]]
        require(relevant <= allowed, f"Positive label is unauthorized: {query_id}")
        require(not forbidden & allowed, f"Forbidden label is authorized: {query_id}")
        if query["category"] == "security":
            require(query["split"] == "security", query_id)
            require(not relevant and forbidden, f"Invalid security fixture: {query_id}")
            require(query["expected_behavior"] == "no_supported_answer", query_id)
        else:
            require(relevant and not forbidden, f"Invalid positive fixture: {query_id}")
            require(query["expected_behavior"] == "supported_answer", query_id)

    env_text = (ROOT / ".env.example").read_text(encoding="utf-8")
    env_lines = [line for line in env_text.splitlines() if line and not line.startswith("#")]
    config = dict(line.split("=", 1) for line in env_lines)
    require(len(config) == len(env_lines), "Duplicate environment variable")
    require(config["SECURERAG_PRINCIPAL_ID"] in principals, "Unknown default principal")
    for key in ("SECURERAG_LLM_BASE_URL", "SECURERAG_LLM_MODEL", "SECURERAG_LLM_API_KEY"):
        require(config[key] == "", f"Provider value must remain empty: {key}")
    require(config["SECURERAG_GENERATION_ENABLED"] == "false", "Generation enabled prematurely")

    print("PASS: preparation fixture consistency only")
    print("Documents: 15; principals: 8; policy combinations checked: 120")
    print("Queries: 48 (dev 18, test 18, security 12)")
    print("Positive labels authorized; forbidden targets denied by fixture oracle")
    print("Provider fields empty; generation disabled")
    print("NOT RUN: model loading, retrieval, application authorization, MCP, generation")


if __name__ == "__main__":
    main()
