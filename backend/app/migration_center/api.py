"""API Migration Center — /api/migrations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.audit.audit_logger import AuditLogger
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.migration_center.exceptions import (
    MigrationAccessDeniedError,
    MigrationCenterError,
    MigrationConflictError,
    MigrationNotFoundError,
    MigrationValidationError,
)
from app.migration_center.schemas import (
    ActivityListOut,
    ActivityOut,
    ProfilePatchIn,
    ProgressOut,
    SessionCancelIn,
    SessionContinueIn,
    SessionCreateIn,
    SessionDetailOut,
    SessionListOut,
    SessionOut,
    SourceCatalogOut,
    SourcesIn,
    TimelineEntryOut,
    TimelineListOut,
)
from app.migration_center.service import MigrationCenterService

router = APIRouter(
    prefix="/migrations",
    tags=["migrations"],
    dependencies=[Depends(require_active_subscription)],
)


def _svc(db: Session) -> MigrationCenterService:
    return MigrationCenterService(db, audit_logger=AuditLogger(db))


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, MigrationNotFoundError):
        return HTTPException(status_code=404, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, MigrationAccessDeniedError):
        return HTTPException(status_code=403, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, MigrationConflictError):
        return HTTPException(status_code=409, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, MigrationValidationError):
        return HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, MigrationCenterError):
        return HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})
    return HTTPException(status_code=400, detail={"code": "migration_error", "message": "Erreur migration"})


def _session_detail(svc: MigrationCenterService, row, org_id: int) -> SessionDetailOut:
    base = SessionOut.model_validate(row)
    timeline = [
        TimelineEntryOut.model_validate(t).model_dump(mode="json")
        for t in svc.list_timeline(row.id, org_id)
    ]
    activities = [
        ActivityOut.model_validate(a).model_dump(mode="json")
        for a in svc.list_activities(row.id, org_id, limit=10)
    ]
    return SessionDetailOut(
        **base.model_dump(),
        timeline=timeline,
        recent_activities=activities,
    )


@router.get("/source-catalog", response_model=SourceCatalogOut)
def source_catalog(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("migration_center.read")
    auth.require_organization_id()
    return SourceCatalogOut(items=_svc(db).get_source_catalog())


@router.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(
    body: SessionCreateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("migration_center.create")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).create_session(
            organization_id=org_id,
            mode=body.mode.value,
            actor_user_id=auth.user_id,
            configuration=body.configuration,
        )
        return SessionOut.model_validate(row)
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/sessions", response_model=SessionListOut)
def list_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    mode: str | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("migration_center.read")
    org_id = auth.require_organization_id()
    items, total = _svc(db).list_sessions(
        organization_id=org_id,
        status=status,
        mode=mode,
        limit=limit,
        offset=offset,
    )
    return SessionListOut(
        items=[SessionOut.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("migration_center.read")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).get_for_org(session_id, org_id)
        return SessionOut.model_validate(row)
    except Exception as exc:
        raise _http(exc) from exc


@router.patch("/sessions/{session_id}/profile", response_model=SessionOut)
def patch_profile(
    session_id: str,
    body: ProfilePatchIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("migration_center.update")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).update_profile(
            session_id,
            org_id,
            body.profile,
            actor_user_id=auth.user_id,
            version=body.version,
        )
        return SessionOut.model_validate(row)
    except Exception as exc:
        raise _http(exc) from exc


@router.patch("/sessions/{session_id}/sources", response_model=SessionOut)
def patch_sources(
    session_id: str,
    body: SourcesIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("migration_center.update")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).update_sources(
            session_id,
            org_id,
            body.source_ids,
            actor_user_id=auth.user_id,
            version=body.version,
        )
        return SessionOut.model_validate(row)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/sessions/{session_id}/continue", response_model=SessionOut)
def continue_session(
    session_id: str,
    body: SessionContinueIn | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("migration_center.update")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).continue_session(
            session_id,
            org_id,
            actor_user_id=auth.user_id,
            version=(body.version if body else None),
        )
        return SessionOut.model_validate(row)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/sessions/{session_id}/cancel", response_model=SessionOut)
def cancel_session(
    session_id: str,
    body: SessionCancelIn | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("migration_center.cancel")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).cancel_session(
            session_id,
            org_id,
            actor_user_id=auth.user_id,
            reason=(body.reason if body else None),
            version=(body.version if body else None),
        )
        return SessionOut.model_validate(row)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/sessions/{session_id}/resume", response_model=SessionDetailOut)
def resume_session(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("migration_center.update")
    org_id = auth.require_organization_id()
    try:
        svc = _svc(db)
        row = svc.resume_session(session_id, org_id, actor_user_id=auth.user_id)
        return _session_detail(svc, row, org_id)
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/sessions/{session_id}/timeline", response_model=TimelineListOut)
def get_timeline(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("migration_center.read")
    org_id = auth.require_organization_id()
    try:
        items = _svc(db).list_timeline(session_id, org_id)
        return TimelineListOut(items=[TimelineEntryOut.model_validate(i) for i in items])
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/sessions/{session_id}/activities", response_model=ActivityListOut)
def get_activities(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("migration_center.read")
    org_id = auth.require_organization_id()
    try:
        items = _svc(db).list_activities(session_id, org_id, limit=limit)
        return ActivityListOut(items=[ActivityOut.model_validate(i) for i in items])
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/sessions/{session_id}/progress", response_model=ProgressOut)
def get_progress(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("migration_center.read")
    org_id = auth.require_organization_id()
    try:
        progress = _svc(db).get_progress(session_id, org_id)
        return ProgressOut(progress=progress)
    except Exception as exc:
        raise _http(exc) from exc
