"""Official MCP stdio server exposing one trusted-identity retrieval tool."""

from __future__ import annotations

import atexit
from typing import Any

from mcp.server.mcpserver import MCPServer

from .identity import get_principal
from .retriever import Retriever
from .settings import Settings

mcp = MCPServer(
    "SecureRAG-MCP",
    instructions=(
        "Search a synthetic enterprise knowledge base. The server binds identity at "
        "process startup; callers cannot select roles or tenants."
    ),
)

_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(Settings.from_env())
    return _retriever


def _close_retriever() -> None:
    global _retriever
    if _retriever is not None:
        _retriever.close()
        _retriever = None


atexit.register(_close_retriever)


@mcp.tool()
def search_knowledge_base(query: str, top_k: int = 5) -> dict[str, Any]:
    """Search only documents authorized for the server-bound demonstration identity."""
    settings = Settings.from_env()
    principal = get_principal(settings.principals_path, settings.principal_id)
    response = get_retriever().search(
        query=query,
        principal=principal,
        mode="hybrid_rerank" if settings.rerank_enabled else "hybrid_rrf",
        top_k=top_k,
    )
    return response.public_dict()


def main() -> None:
    get_retriever()
    mcp.run()


if __name__ == "__main__":
    main()
