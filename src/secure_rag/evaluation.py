"""Deterministic retrieval and authorization evaluation over the frozen fixtures."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any

from .identity import is_authorized, load_principals
from .retriever import Retriever
from .schemas import RetrievalMode, SearchHit
from .settings import PROJECT_ROOT, Settings

BASE_MODES: tuple[RetrievalMode, ...] = ("dense", "sparse", "hybrid_rrf")
CATEGORY_ORDER = ("exact", "semantic", "ordinary", "hard", "comparison")


def load_benchmark(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def unique_document_ids(hits: tuple[SearchHit, ...] | list[SearchHit]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for hit in hits:
        if hit.document_id not in seen:
            seen.add(hit.document_id)
            ordered.append(hit.document_id)
    return ordered


def query_metrics(relevant: set[str], retrieved: list[str]) -> dict[str, float]:
    top1 = retrieved[:1]
    top3 = retrieved[:3]
    top5 = retrieved[:5]
    first_rank = next(
        (index for index, document_id in enumerate(top5, 1) if document_id in relevant),
        None,
    )
    dcg_at_5 = sum(
        1.0 / math.log2(rank + 1)
        for rank, document_id in enumerate(retrieved[:5], 1)
        if document_id in relevant
    )
    ideal_hits = min(len(relevant), 5)
    ideal_dcg_at_5 = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return {
        "hit_at_1": float(bool(relevant & set(top1))),
        "hit_at_3": float(bool(relevant & set(top3))),
        "recall_at_3": len(relevant & set(top3)) / len(relevant),
        "mrr_at_5": 0.0 if first_rank is None else 1.0 / first_rank,
        "ndcg_at_5": dcg_at_5 / ideal_dcg_at_5,
    }


def _averages(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {
            name: 0.0
            for name in ("hit_at_1", "hit_at_3", "recall_at_3", "mrr_at_5", "ndcg_at_5")
        }
    return {name: fmean(row[name] for row in rows) for name in rows[0]}


def evaluate(settings: Settings, benchmark_path: Path) -> dict[str, Any]:
    benchmark = load_benchmark(benchmark_path)
    modes = BASE_MODES + (("hybrid_rerank",) if settings.rerank_enabled else ())
    principals = load_principals(settings.principals_path)
    retriever = Retriever(settings)
    positive_rows: dict[str, dict[str, list[dict[str, float]]]] = {
        mode: defaultdict(list) for mode in modes
    }
    details: list[dict[str, Any]] = []
    security_returned = 0
    security_unauthorized = 0
    security_queries_with_violation: set[tuple[str, str]] = set()

    try:
        for case in benchmark:
            principal = principals[case["principal_id"]]
            for mode in modes:
                response = retriever.search(
                    case["query"], principal, mode=mode, top_k=settings.top_k
                )
                if mode == "hybrid_rerank" and response.retrieval_mode != mode:
                    raise RuntimeError(f"Reranker evaluation fell back: {response.warning}")
                retrieved = unique_document_ids(response.results)
                row: dict[str, Any] = {
                    "id": case["id"],
                    "split": case["split"],
                    "category": case["category"],
                    "mode": mode,
                    "principal_id": principal.principal_id,
                    "retrieved_document_ids": retrieved,
                }
                if case["category"] == "security":
                    forbidden = set(case.get("forbidden_document_ids", []))
                    unauthorized = [
                        hit.document_id
                        for hit in response.results
                        if not is_authorized(principal, hit)
                        or hit.document_id in forbidden
                    ]
                    security_returned += len(response.results)
                    security_unauthorized += len(unauthorized)
                    if unauthorized:
                        security_queries_with_violation.add((case["id"], mode))
                    row["unauthorized_document_ids"] = unauthorized
                else:
                    metrics = query_metrics(
                        set(case["relevant_document_ids"]), retrieved
                    )
                    row.update(metrics)
                    positive_rows[mode][case["split"]].append(metrics)
                    positive_rows[mode][case["category"]].append(metrics)
                    positive_rows[mode]["all"].append(metrics)
                details.append(row)
    finally:
        retriever.close()

    summary = {
        mode: {group: _averages(rows) for group, rows in groups.items()}
        for mode, groups in positive_rows.items()
    }
    security = {
        "unauthorized_candidates": security_unauthorized,
        "returned_candidates": security_returned,
        "unauthorized_candidate_rate": (
            0.0 if security_returned == 0 else security_unauthorized / security_returned
        ),
        "query_mode_pairs_with_violation": len(security_queries_with_violation),
        "security_queries": sum(1 for case in benchmark if case["category"] == "security"),
        "modes_checked": list(modes),
    }
    return {
        "models": {
            "dense": settings.dense_model,
            "sparse": settings.sparse_model,
            "reranker": settings.rerank_model if settings.rerank_enabled else None,
        },
        "collection": settings.collection_name,
        "positive_query_count": sum(
            1 for case in benchmark if case["category"] != "security"
        ),
        "summary": summary,
        "security": security,
        "details": details,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SecureRAG-MCP 固定基准评测",
        "",
        f"- Dense：`{report['models']['dense']}`",
        f"- Sparse：`{report['models']['sparse']}`",
        f"- Reranker：`{report['models']['reranker'] or 'disabled'}`",
        f"- 正例查询：{report['positive_query_count']}",
        "",
        "## 检索指标",
        "",
        "| 模式 | 分组 | Hit@1 | Hit@3 | Recall@3 | MRR@5 | nDCG@5 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for mode, groups in report["summary"].items():
        for group in ("dev", "test", *CATEGORY_ORDER, "all"):
            if group not in groups:
                continue
            metrics = groups[group]
            lines.append(
                f"| {mode} | {group} | {metrics['hit_at_1']:.3f} | "
                f"{metrics['hit_at_3']:.3f} | {metrics['recall_at_3']:.3f} | "
                f"{metrics['mrr_at_5']:.3f} | {metrics['ndcg_at_5']:.3f} |"
            )
    security = report["security"]
    lines.extend(
        [
            "",
            "## 权限安全检查",
            "",
            f"- 安全查询数：{security['security_queries']}",
            f"- 检查模式：{', '.join(security['modes_checked'])}",
            f"- 返回候选总数：{security['returned_candidates']}",
            f"- 未授权候选数：{security['unauthorized_candidates']}",
            f"- 未授权候选率：{security['unauthorized_candidate_rate']:.6f}",
            f"- 出现越权的查询/模式组合：{security['query_mode_pairs_with_violation']}",
            "",
            "> 该结果只覆盖当前小规模合成测试集，不代表生产环境的普遍安全证明。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen retrieval benchmark")
    parser.add_argument(
        "--benchmark", type=Path, default=PROJECT_ROOT / "data/benchmark.jsonl"
    )
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports")
    parser.add_argument("--report-name", default="latest")
    args = parser.parse_args()

    report = evaluate(Settings.from_env(), args.benchmark)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{args.report_name}.json"
    markdown_path = args.output_dir / f"{args.report_name}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(markdown_path)


if __name__ == "__main__":
    main()

