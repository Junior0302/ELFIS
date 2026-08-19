"""Routes Launch Dashboard C1.12."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dashboard_launch.schemas import AccountingDiscoveredOut, LaunchDashboardOut
from app.dashboard_launch.service import LaunchDashboardService
from app.database import get_db
from app.deps import AuthContext, get_auth_context

router = APIRouter(prefix="/dashboard", tags=["dashboard-launch"])


@router.get("/launch", response_model=LaunchDashboardOut)
def get_launch_dashboard(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    organization_id = auth.require_organization_id()
    return LaunchDashboardService(db).build(
        organization_id=organization_id,
        user=auth.user,
        permissions=list(auth.permissions or []),
    )


@router.post("/launch/accounting-discovered", response_model=AccountingDiscoveredOut)
def mark_accounting_discovered(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Marque la découverte de l’espace comptable (checklist accounting_discovery)."""
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    organization_id = auth.require_organization_id()
    auth.require_any(["ai.analysis", "documents.read", "accounting.view"])
    LaunchDashboardService(db).mark_accounting_discovered(
        organization_id=organization_id,
        user_id=auth.user.id,
    )
    return AccountingDiscoveredOut()
