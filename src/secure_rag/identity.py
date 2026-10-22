"""Trusted local identities and the authorization policy used before retrieval."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from qdrant_client import models

from .schemas import Principal, SearchHit


def load_principals(path: Path) -> dict[str, Principal]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["principals"]
    principals: dict[str, Principal] = {}
    for principal_id, item in raw.items():
        principals[principal_id] = Principal(
            principal_id=principal_id,
            tenant_id=str(item["tenant_id"]),
            department=str(item["department"]),
            roles=tuple(str(role) for role in item["roles"]),
            max_clearance_rank=int(item["max_clearance_rank"]),
        )
    return principals


def get_principal(path: Path, principal_id: str) -> Principal:
    principals = load_principals(path)
    try:
        return principals[principal_id]
    except KeyError as exc:
        raise ValueError(f"Unknown principal: {principal_id}") from exc


def is_authorized(principal: Principal, item: SearchHit | dict[str, Any]) -> bool:
    if isinstance(item, SearchHit):
        tenant_id = item.tenant_id
        department = item.department
        clearance_rank = item.clearance_rank
        allowed_roles = item.allowed_roles
    else:
        tenant_id = str(item["tenant_id"])
        department = str(item["department"])
        clearance_rank = int(item["clearance_rank"])
        allowed_roles = tuple(str(role) for role in item["allowed_roles"])
    return (
        tenant_id == principal.tenant_id
        and clearance_rank <= principal.max_clearance_rank
        and department in (principal.department, "shared")
        and bool(set(principal.roles) & set(allowed_roles))
    )


def build_qdrant_filter(principal: Principal) -> models.Filter:
    """Build the same four-part policy as the pure Python authorization oracle."""
    return models.Filter(
        must=[
            models.FieldCondition(
                key="tenant_id", match=models.MatchValue(value=principal.tenant_id)
            ),
            models.FieldCondition(
                key="clearance_rank",
                range=models.Range(lte=principal.max_clearance_rank),
            ),
            models.FieldCondition(
                key="allowed_roles",
                match=models.MatchAny(any=list(principal.roles)),
            ),
        ],
        should=[
            models.FieldCondition(
                key="department", match=models.MatchValue(value=principal.department)
            ),
            models.FieldCondition(
                key="department", match=models.MatchValue(value="shared")
            ),
        ],
    )


def assert_authorized(principal: Principal, hits: list[SearchHit] | tuple[SearchHit, ...]) -> None:
    unauthorized = [hit.chunk_id for hit in hits if not is_authorized(principal, hit)]
    if unauthorized:
        raise PermissionError(
            f"Authorization invariant violated for {principal.principal_id}: {unauthorized}"
        )
