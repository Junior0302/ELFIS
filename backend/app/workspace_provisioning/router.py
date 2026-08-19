"""Routes API — Workspace Provisioning V1."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.workspace_provisioning.schemas import (
    WorkspaceProvisionRequest,
    WorkspaceProvisionStatusOut,
)
from app.workspace_provisioning.service import WorkspaceProvisioningService

router = APIRouter(prefix="/workspace", tags=["workspace-provisioning"])


@router.get("/provision/status", response_model=WorkspaceProvisionStatusOut)
def get_provision_status(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    organization_id = auth.require_organization_id()
    return WorkspaceProvisioningService(db).get_status(organization_id)


@router.post("/provision", response_model=WorkspaceProvisionStatusOut)
def start_provision(
    body: WorkspaceProvisionRequest,
    request: Request,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    auth.require("settings.manage")
    organization_id = auth.require_organization_id()
    ip = request.client.host if request.client else None
    try:
        # Re-validate explicitly for stable error code
        payload = WorkspaceProvisionRequest.model_validate(body.model_dump())
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_SETUP_DRAFT",
                "message": "Les informations de configuration sont invalides.",
                "errors": exc.errors(),
            },
        ) from exc

    return WorkspaceProvisioningService(db).provision(
        organization_id=organization_id,
        user_id=auth.user.id,
        payload=payload,
        ip=ip,
    )
