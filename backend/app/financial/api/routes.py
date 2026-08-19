"""Endpoints Financial Dashboard V1.

/financial/overview     — tout le dashboard en un appel (KPIs, alertes, score…)
/financial/kpis         — les 9 indicateurs standardisés
/financial/trends       — tendances mensuelles / hebdomadaires / annuelles
/financial/charts       — séries prêtes à afficher (le frontend ne calcule rien)
/financial/alerts       — alertes normalisées
/financial/health-score — Financial Health Score (0-100, documenté)

/platform/financial/overview — Cockpit Admin (toutes organisations)

``?refresh=true`` force le recalcul (bypass du cache TTL).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import (
    AuthContext,
    get_auth_context,
    require_active_subscription,
    require_platform_admin,
)
from app.financial.alerts import build_alerts
from app.financial.engine import FinancialEngine
from app.financial.health import compute_health_score
from app.financial.platform_service import FinancialPlatformService

router = APIRouter(
    prefix="/financial",
    tags=["financial"],
    dependencies=[Depends(require_active_subscription)],
)

admin_router = APIRouter(
    prefix="/platform/financial",
    tags=["platform-financial"],
    dependencies=[Depends(require_platform_admin)],
)


def _engine(db: Session) -> FinancialEngine:
    return FinancialEngine(db)


@router.get("/overview")
def financial_overview(
    refresh: bool = Query(default=False),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = auth.require_organization_id()
    return _engine(db).overview(org_id, refresh=refresh)


@router.get("/kpis")
def financial_kpis(
    refresh: bool = Query(default=False),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = auth.require_organization_id()
    return {"kpis": [k.model_dump() for k in _engine(db).kpis(org_id, refresh=refresh)]}


@router.get("/trends")
def financial_trends(
    refresh: bool = Query(default=False),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = auth.require_organization_id()
    return _engine(db).trends(org_id, refresh=refresh)


@router.get("/charts")
def financial_charts(
    refresh: bool = Query(default=False),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = auth.require_organization_id()
    return _engine(db).charts(org_id, refresh=refresh)


@router.get("/alerts")
def financial_alerts(
    refresh: bool = Query(default=False),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = auth.require_organization_id()
    snap = _engine(db).snapshot(org_id, refresh=refresh)
    return {"alerts": [a.model_dump() for a in build_alerts(snap)]}


@router.get("/health-score")
def financial_health_score(
    refresh: bool = Query(default=False),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = auth.require_organization_id()
    snap = _engine(db).snapshot(org_id, refresh=refresh)
    return compute_health_score(snap)


@admin_router.get("/overview")
def platform_financial_overview(db: Session = Depends(get_db)):
    return FinancialPlatformService(db).platform_overview()
