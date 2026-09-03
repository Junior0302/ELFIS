"""API Work Queue."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.work_queue.enums import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, MAX_SEARCH_LENGTH
from app.work_queue.schemas import WorkQueueOut
from app.work_queue.service import WorkQueueService

router = APIRouter(
    prefix="/work-queue",
    tags=["work-queue"],
    dependencies=[Depends(require_active_subscription)],
)


@router.get("", response_model=WorkQueueOut)
def get_work_queue(
    bucket: str | None = Query("todo"),
    severity: str | None = Query(None),
    decision_type: str | None = Query(None),
    source_type: str | None = Query(None),
    search: str | None = Query(None, max_length=MAX_SEARCH_LENGTH),
    sort: str = Query("priority"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    sync: bool = Query(False),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    org_id = auth.require_organization_id()
    return WorkQueueService(db).get_queue(
        organization_id=org_id,
        permissions=list(auth.permissions or []),
        bucket=bucket,
        severity=severity,
        decision_type=decision_type,
        source_type=source_type,
        search=search,
        sort=sort,
        page=page,
        page_size=page_size,
        sync=sync,
    )
