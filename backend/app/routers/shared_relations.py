"""ELFIS Shared Relations API — read projections over existing identity tables (S1.2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.services.auth import write_audit
from app.services.shared_relations import (
    get_shared_relation,
    get_shared_relation_detail,
    list_duplicate_candidates,
    list_shared_relations,
)

router = APIRouter(
    prefix="/shared/relations",
    tags=["shared-relations"],
    dependencies=[Depends(require_active_subscription)],
)


def _can_read_relations(auth: AuthContext) -> None:
    """Map temporaire → permissions existantes (pas encore platform.relations.*)."""
    auth.require_any(["invoice.read", "documents.read", "ai.analysis", "*"])


@router.get("")
def list_relations(
    q: str | None = Query(None),
    role: str | None = Query(None),
    source: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _can_read_relations(auth)
    org_id = auth.require_organization_id()
    result = list_shared_relations(
        db,
        organization_id=org_id,
        q=q,
        role=role,
        source=source,
        status=status,
        page=page,
        page_size=page_size,
    )
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=org_id,
        action="shared_relations.list",
        module="platform",
    )
    return result.model_dump(mode="json")


@router.get("/search")
def search_relations(
    q: str = Query("", min_length=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _can_read_relations(auth)
    org_id = auth.require_organization_id()
    result = list_shared_relations(
        db,
        organization_id=org_id,
        q=q or None,
        page=page,
        page_size=page_size,
    )
    return result.model_dump(mode="json")


@router.get("/duplicates")
def list_duplicates(
    relation_id: str | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _can_read_relations(auth)
    org_id = auth.require_organization_id()
    items = list_duplicate_candidates(db, organization_id=org_id, relation_id=relation_id)
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=org_id,
        action="shared_relations.duplicates",
        module="platform",
    )
    return {
        "items": [d.model_dump(mode="json") for d in items],
        "auto_merge": False,
        "note": "Détection non destructive — aucune fusion automatique.",
    }


@router.get("/{relation_id}")
def get_relation(
    relation_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _can_read_relations(auth)
    org_id = auth.require_organization_id()
    detail = get_shared_relation_detail(
        db, organization_id=org_id, relation_id=relation_id
    )
    if not detail:
        raise HTTPException(404, detail="Relation introuvable")
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=org_id,
        action=f"shared_relations.get:{relation_id}",
        module="platform",
    )
    return detail.model_dump(mode="json")


@router.get("/{relation_id}/roles")
def get_relation_roles(
    relation_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _can_read_relations(auth)
    org_id = auth.require_organization_id()
    rel = get_shared_relation(db, organization_id=org_id, relation_id=relation_id)
    if not rel:
        raise HTTPException(404, detail="Relation introuvable")
    return {"id": rel.id, "roles": rel.roles}


@router.get("/{relation_id}/duplicates")
def get_relation_duplicates(
    relation_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _can_read_relations(auth)
    org_id = auth.require_organization_id()
    rel = get_shared_relation(db, organization_id=org_id, relation_id=relation_id)
    if not rel:
        raise HTTPException(404, detail="Relation introuvable")
    items = list_duplicate_candidates(db, organization_id=org_id, relation_id=relation_id)
    return {
        "id": relation_id,
        "items": [d.model_dump(mode="json") for d in items],
        "auto_merge": False,
    }
