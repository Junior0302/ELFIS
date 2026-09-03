"""Routes Command Center C1.14."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dashboard_command_center.schemas import CommandCenterOut
from app.dashboard_command_center.service import CommandCenterService
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard-command-center"],
    dependencies=[Depends(require_active_subscription)],
)


@router.get("/command-center", response_model=CommandCenterOut)
def get_command_center(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    organization_id = auth.require_organization_id()
    return CommandCenterService(db).build(
        organization_id=organization_id,
        user=auth.user,
        permissions=list(auth.permissions or []),
    )
