"""Sales Operations API — /api/sales/ops/*."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.sales_crm.permissions import SALES_MANAGE, SALES_READ, SALES_WRITE
from app.sales_operations.schemas import (
    BulkActionIn,
    BulkActionOut,
    CalendarOut,
    DuplicateResolveIn,
    DuplicateScanOut,
    ImportCommitIn,
    ImportCommitOut,
    ImportPreviewIn,
    ImportPreviewOut,
    JournalOut,
    SavedViewCreate,
    SavedViewOut,
    SavedViewUpdate,
)
from app.sales_operations.service import SalesOperationsService
from app.services.auth import write_audit

router = APIRouter(prefix="/sales/ops", tags=["sales-operations"])


def _uid(auth: AuthContext) -> int | None:
    return auth.user.id if auth.user else None


@router.get("/saved-views", response_model=list[SavedViewOut])
def list_saved_views(
    resource: str | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    rows = SalesOperationsService(db).list_saved_views(
        organization_id=org_id, user_id=_uid(auth), resource=resource
    )
    return [SavedViewOut.model_validate(r) for r in rows]


@router.post("/saved-views", response_model=SavedViewOut, status_code=201)
def create_saved_view(
    body: SavedViewCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = SalesOperationsService(db).create_saved_view(
        organization_id=org_id, user_id=_uid(auth), data=body
    )
    db.commit()
    return SavedViewOut.model_validate(row)


@router.patch("/saved-views/{view_id}", response_model=SavedViewOut)
def update_saved_view(
    view_id: int,
    body: SavedViewUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = SalesOperationsService(db).update_saved_view(
        organization_id=org_id, user_id=_uid(auth), view_id=view_id, data=body
    )
    db.commit()
    return SavedViewOut.model_validate(row)


@router.delete("/saved-views/{view_id}", status_code=204)
def delete_saved_view(
    view_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    SalesOperationsService(db).delete_saved_view(organization_id=org_id, view_id=view_id)
    db.commit()
    return None


@router.get("/calendar", response_model=CalendarOut)
def sales_calendar(
    from_date: date = Query(...),
    to_date: date = Query(...),
    include_tasks: bool = True,
    include_activities: bool = True,
    include_closings: bool = True,
    include_proposals: bool = True,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    return SalesOperationsService(db).build_calendar(
        organization_id=org_id,
        from_date=from_date,
        to_date=to_date,
        include_tasks=include_tasks,
        include_activities=include_activities,
        include_closings=include_closings,
        include_proposals=include_proposals,
    )


@router.post("/import/preview", response_model=ImportPreviewOut)
def import_preview(
    body: ImportPreviewIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    return SalesOperationsService(db).preview_import(organization_id=org_id, data=body)


@router.post("/import/commit", response_model=ImportCommitOut)
def import_commit(
    body: ImportCommitIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    out = SalesOperationsService(db).commit_import(
        organization_id=org_id, user_id=_uid(auth), data=body
    )
    db.commit()
    write_audit(
        db,
        user_id=_uid(auth),
        organization_id=org_id,
        action="sales.import.completed",
        module="sales",
    )
    return out


@router.get("/duplicates/{resource}", response_model=DuplicateScanOut)
def scan_duplicates(
    resource: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    if resource not in ("leads", "companies", "people"):
        raise HTTPException(400, detail={"code": "invalid_resource", "message": "Resource invalide"})
    org_id = auth.require_organization_id()
    return SalesOperationsService(db).scan_duplicates(organization_id=org_id, resource=resource)


@router.post("/duplicates/resolve")
def resolve_duplicate(
    body: DuplicateResolveIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_MANAGE)
    org_id = auth.require_organization_id()
    out = SalesOperationsService(db).resolve_duplicate(
        organization_id=org_id, user_id=_uid(auth), data=body
    )
    db.commit()
    return out


@router.post("/bulk", response_model=BulkActionOut)
def bulk_action(
    body: BulkActionIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_MANAGE)
    org_id = auth.require_organization_id()
    out = SalesOperationsService(db).bulk_action(
        organization_id=org_id, user_id=_uid(auth), data=body
    )
    db.commit()
    write_audit(
        db,
        user_id=_uid(auth),
        organization_id=org_id,
        action=f"sales.bulk.{body.action}",
        module="sales",
    )
    return out


@router.get("/journal", response_model=JournalOut)
def my_journal(
    limit: int = Query(50, ge=1, le=100),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    return SalesOperationsService(db).my_activity(
        organization_id=org_id, user_id=_uid(auth), limit=limit
    )
