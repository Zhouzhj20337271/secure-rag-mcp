"""Human-readable local search entry point."""

from __future__ import annotations

import argparse
import json

from .identity import get_principal
from .retriever import Retriever
from .settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the authorized local knowledge base")
    parser.add_argument("query")
    parser.add_argument("--principal", help="Server-selected demo identity")
    parser.add_argument(
        "--mode",
        choices=("dense", "sparse", "hybrid_rrf", "hybrid_rerank"),
        default="hybrid_rrf",
    )
    parser.add_argument("--top-k", type=int)
    args = parser.parse_args()

    settings = Settings.from_env()
    principal = get_principal(
        settings.principals_path, args.principal or settings.principal_id
    )
    retriever = Retriever(settings)
    try:
        response = retriever.search(args.query, principal, args.mode, args.top_k)
    finally:
        retriever.close()
    print(json.dumps(response.public_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

