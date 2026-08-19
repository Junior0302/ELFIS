from __future__ import annotations

"""
Legacy dashboard endpoints.

Migration (2026-07) : les surfaces client Accueil (/dashboard) et Cockpit (/cockpit)
consomment le Financial Engine via `/api/financial/*`.

Ces routes restent exposées temporairement pour compatibilité éventuelle
(intégrations externes / anciens clients). Ne plus les utiliser dans le frontend.
Plan : suppression après fenêtre de dépréciation (prochaine major).
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models import Invoice
from app.schemas import DashboardStats
from app.services.finance_agent import pilot_kpis
from app.services.serializers import serialize_invoice

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard-legacy-deprecated"],
    dependencies=[Depends(require_active_subscription)],
)

_DEPRECATION = (
    "Deprecated: use /api/financial/overview (Financial Engine). "
    "Will be removed in a future major release."
)


@router.get("/stats", response_model=DashboardStats, deprecated=True)
def dashboard_stats(
    response: Response,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """DEPRECATED — agrégats Invoice locaux. Préférer Financial Engine."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Sat, 01 Aug 2026 00:00:00 GMT"
    response.headers["Link"] = '</api/financial/overview>; rel="successor-version"'
    response.headers["X-ComptaPilot-Deprecated"] = _DEPRECATION
    auth.require("invoice.read")
    query = db.query(Invoice).filter(
        Invoice.organization_id == auth.require_organization_id()
    )
    invoice_count = query.count()
    total_ht = query.with_entities(func.coalesce(func.sum(Invoice.amount_ht), 0.0)).scalar() or 0.0
    recoverable_vat = (
        query.with_entities(func.coalesce(func.sum(Invoice.amount_tva), 0.0)).scalar() or 0.0
    )
    to_review = query.filter(Invoice.needs_review.is_(True)).count()
    recent = query.order_by(Invoice.created_at.desc()).limit(8).all()
    return DashboardStats(
        invoice_count=invoice_count,
        total_ht=float(total_ht),
        recoverable_vat=float(recoverable_vat),
        to_review=to_review,
        recent=[serialize_invoice(i) for i in recent],
    )


@router.get("/pilot", deprecated=True)
def dashboard_pilot(
    response: Response,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """DEPRECATED — pilot_kpis legacy. Préférer Financial Engine."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Sat, 01 Aug 2026 00:00:00 GMT"
    response.headers["Link"] = '</api/financial/overview>; rel="successor-version"'
    response.headers["X-ComptaPilot-Deprecated"] = _DEPRECATION
    return pilot_kpis(db, auth.require_organization_id())
