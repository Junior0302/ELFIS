"""Sales Intelligence API — /api/sales/intelligence*."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.sales_crm.permissions import SALES_ADMIN, SALES_MANAGE, SALES_READ
from app.sales_intelligence.permissions import INTEL_DISMISS, INTEL_MANAGE, INTEL_READ, INTEL_SYNC
from app.sales_intelligence.schemas import (
    DismissIn,
    InsightListOut,
    InsightOut,
    IntelligenceOverviewOut,
    SyncOut,
)
from app.sales_intelligence.service import SalesIntelligenceService
from app.services.auth import write_audit

router = APIRouter(prefix="/sales/intelligence", tags=["sales-intelligence"])


def _has(auth: AuthContext, *codes: str) -> bool:
    perms = auth.permissions or []
    if "*" in perms:
        return True
    return any(code in perms for code in codes)


def _require(auth: AuthContext, *codes: str) -> None:
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    if not _has(auth, *codes):
        raise HTTPException(
            403,
            detail={"code": "permission_denied", "message": "Permission refusée"},
        )


def _uid(auth: AuthContext) -> int | None:
    return auth.user.id if auth.user else None


def _insight_out(row) -> InsightOut:
    return InsightOut.model_validate(row)


@router.get("", response_model=IntelligenceOverviewOut)
def intelligence_overview(
    sync: bool = Query(True, description="Synchroniser avant lecture"),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require(auth, INTEL_READ, SALES_READ, SALES_MANAGE, SALES_ADMIN, "*")
    org_id = auth.require_organization_id()
    out = SalesIntelligenceService(db).build_overview(
        organization_id=org_id, auto_sync=sync
    )
    db.commit()
    return out


@router.get("/insights", response_model=InsightListOut)
def list_insights(
    category: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: str = "-priority_score",
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require(auth, INTEL_READ, SALES_READ, SALES_MANAGE, SALES_ADMIN, "*")
    org_id = auth.require_organization_id()
    items, total = SalesIntelligenceService(db).repo.list_filtered(
        organization_id=org_id,
        category=category,
        severity=severity,
        status=status,
        source_type=source_type,
        source_id=source_id,
        page=page,
        limit=limit,
        sort=sort,
    )
    return InsightListOut(
        items=[_insight_out(i) for i in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/insights/{insight_id}", response_model=InsightOut)
def get_insight(
    insight_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require(auth, INTEL_READ, SALES_READ, SALES_MANAGE, SALES_ADMIN, "*")
    org_id = auth.require_organization_id()
    row = SalesIntelligenceService(db).get_insight(
        organization_id=org_id, insight_id=insight_id
    )
    return _insight_out(row)


@router.post("/insights/{insight_id}/acknowledge", response_model=InsightOut)
def acknowledge_insight(
    insight_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require(auth, INTEL_READ, SALES_READ, SALES_MANAGE, SALES_ADMIN, "*")
    org_id = auth.require_organization_id()
    row = SalesIntelligenceService(db).acknowledge(
        organization_id=org_id, insight_id=insight_id, user_id=_uid(auth)
    )
    db.commit()
    write_audit(
        db,
        user_id=_uid(auth),
        organization_id=org_id,
        action="sales.insight.acknowledged",
        module="sales",
    )
    return _insight_out(row)


@router.post("/insights/{insight_id}/dismiss", response_model=InsightOut)
def dismiss_insight(
    insight_id: int,
    body: DismissIn | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require(auth, INTEL_DISMISS, INTEL_MANAGE, SALES_MANAGE, SALES_ADMIN, "*")
    org_id = auth.require_organization_id()
    row = SalesIntelligenceService(db).dismiss(
        organization_id=org_id,
        insight_id=insight_id,
        user_id=_uid(auth),
        reason=(body.reason if body else None),
    )
    db.commit()
    write_audit(
        db,
        user_id=_uid(auth),
        organization_id=org_id,
        action="sales.insight.dismissed",
        module="sales",
    )
    return _insight_out(row)


@router.post("/sync", response_model=SyncOut)
def sync_insights(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require(auth, INTEL_SYNC, INTEL_MANAGE, SALES_MANAGE, SALES_ADMIN, "*")
    org_id = auth.require_organization_id()
    out = SalesIntelligenceService(db).sync(
        organization_id=org_id, user_id=_uid(auth)
    )
    db.commit()
    write_audit(
        db,
        user_id=_uid(auth),
        organization_id=org_id,
        action="sales.insight.sync",
        module="sales",
    )
    return out
