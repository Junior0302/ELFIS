"""API Decision Center + Execution Layer."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.decision_center.execution import DecisionExecutionService
from app.decision_center.schemas import (
    DecisionDetailOut,
    DecisionExecuteOut,
    DecisionExecuteRequest,
    DecisionListOut,
    DecisionMutationOut,
)
from app.decision_center.service import DecisionCenterService
from app.deps import AuthContext, get_auth_context, require_active_subscription

router = APIRouter(
    prefix="/decisions",
    tags=["decision-center"],
    dependencies=[Depends(require_active_subscription)],
)


@router.get("", response_model=DecisionListOut)
def list_decisions(
    status: str | None = None,
    severity: str | None = None,
    source_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
    sync: bool = True,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    org_id = auth.require_organization_id()
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    return DecisionCenterService(db).list_for_user(
        organization_id=org_id,
        permissions=list(auth.permissions or []),
        status=status,
        severity=severity,
        source_type=source_type,
        page=page,
        page_size=page_size,
        sync=sync,
    )


@router.get("/{decision_id}", response_model=DecisionDetailOut)
def get_decision(
    decision_id: str,
    sync: bool = True,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    org_id = auth.require_organization_id()
    return DecisionCenterService(db).get_detail(
        organization_id=org_id,
        decision_id=decision_id,
        permissions=list(auth.permissions or []),
        sync=sync,
    )


@router.post("/{decision_id}/dismiss", response_model=DecisionMutationOut)
def dismiss_decision(
    decision_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    org_id = auth.require_organization_id()
    decision = DecisionCenterService(db).dismiss(
        organization_id=org_id,
        decision_id=decision_id,
        permissions=list(auth.permissions or []),
        user_id=auth.user.id,
    )
    return DecisionMutationOut(decision=decision)


@router.post("/{decision_id}/start", response_model=DecisionDetailOut)
def start_decision(
    decision_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    from app.work_queue.service import WorkQueueService

    org_id = auth.require_organization_id()
    return WorkQueueService(db).start(
        organization_id=org_id,
        decision_id=decision_id,
        permissions=list(auth.permissions or []),
        user_id=auth.user.id,
    )


@router.post("/{decision_id}/reopen", response_model=DecisionDetailOut)
def reopen_decision(
    decision_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    from app.work_queue.service import WorkQueueService

    org_id = auth.require_organization_id()
    return WorkQueueService(db).reopen_dismissed(
        organization_id=org_id,
        decision_id=decision_id,
        permissions=list(auth.permissions or []),
        user_id=auth.user.id,
    )


@router.post("/{decision_id}/actions/{action_type}", response_model=DecisionExecuteOut)
def execute_decision_action(
    decision_id: str,
    action_type: str,
    body: DecisionExecuteRequest | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    org_id = auth.require_organization_id()
    svc = DecisionCenterService(db)
    return DecisionExecutionService(db, svc).execute(
        organization_id=org_id,
        decision_id=decision_id,
        action_type=action_type,
        permissions=list(auth.permissions or []),
        user_id=auth.user.id,
        body=body,
    )
