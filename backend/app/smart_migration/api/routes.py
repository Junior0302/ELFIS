"""API Smart Migration — /api/migration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.smart_migration.exceptions import (
    SmartConfirmationRequiredError,
    SmartConflictError,
    SmartMigrationError,
    SmartNotFoundError,
    SmartStateError,
)
from app.smart_migration.orchestrator import SmartMigrationOrchestrator
from app.smart_migration.schemas import (
    CancelOut,
    CleanupIn,
    DashboardOut,
    MetricsOut,
    ReportOut,
    RestartBatchIn,
    RestartBatchOut,
    ResumeOut,
    RetryFailedOut,
    StartIn,
    StatusOut,
)

router = APIRouter(
    prefix="/migration",
    tags=["smart-migration"],
    dependencies=[Depends(require_active_subscription)],
)


def _orch(db: Session) -> SmartMigrationOrchestrator:
    return SmartMigrationOrchestrator(db)


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, SmartNotFoundError):
        return HTTPException(
            status_code=404, detail={"code": exc.code, "message": exc.message}
        )
    if isinstance(exc, (SmartConflictError, SmartStateError)):
        return HTTPException(
            status_code=409, detail={"code": exc.code, "message": exc.message}
        )
    if isinstance(exc, SmartConfirmationRequiredError):
        return HTTPException(
            status_code=400, detail={"code": exc.code, "message": exc.message}
        )
    if isinstance(exc, SmartMigrationError):
        return HTTPException(
            status_code=400, detail={"code": exc.code, "message": exc.message}
        )
    return HTTPException(
        status_code=400,
        detail={"code": "smart_migration_error", "message": "Erreur smart migration"},
    )


@router.get("/status", response_model=StatusOut)
def get_status(
    migration_session_id: str = Query(..., alias="migration_id"),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("smart_migration.read")
    org_id = auth.require_organization_id()
    data = _orch(db).status(
        organization_id=org_id, migration_session_id=migration_session_id
    )
    return StatusOut(**data)


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(
    migration_session_id: str = Query(..., alias="migration_id"),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("smart_migration.read")
    org_id = auth.require_organization_id()
    data = _orch(db).dashboard(
        organization_id=org_id, migration_session_id=migration_session_id
    )
    return DashboardOut(data=data)


@router.get("/metrics", response_model=MetricsOut)
def get_metrics(
    migration_session_id: str = Query(..., alias="migration_id"),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("smart_migration.read")
    org_id = auth.require_organization_id()
    data = _orch(db).metrics(
        organization_id=org_id, migration_session_id=migration_session_id
    )
    return MetricsOut(data=data)


@router.get("/report", response_model=ReportOut)
def get_report(
    migration_session_id: str = Query(..., alias="migration_id"),
    fmt: str = Query("json", alias="format"),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("smart_migration.report")
    org_id = auth.require_organization_id()
    try:
        data = _orch(db).get_report(
            organization_id=org_id,
            migration_session_id=migration_session_id,
            fmt=fmt,
        )
        return ReportOut(data=data)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/start", response_model=ResumeOut)
def start_migration(
    body: StartIn,
    migration_session_id: str = Query(..., alias="migration_id"),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("smart_migration.run")
    org_id = auth.require_organization_id()
    try:
        orch = _orch(db)
        if body.run_now:
            run = orch.run_orchestration(
                organization_id=org_id,
                migration_session_id=migration_session_id,
                actor_user_id=auth.user_id,
                batch_size=body.batch_size,
                max_workers=body.max_workers,
                parallel=body.parallel,
            )
        else:
            run = orch.start_or_get_run(
                organization_id=org_id,
                migration_session_id=migration_session_id,
                actor_user_id=auth.user_id,
                batch_size=body.batch_size,
                max_workers=body.max_workers,
                parallel=body.parallel,
            )
        return ResumeOut(
            smart_run_id=run.id,
            status=run.status,
            progress_percent=float(run.progress_percent or 0),
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/resume", response_model=ResumeOut)
def resume_migration(
    migration_session_id: str = Query(..., alias="migration_id"),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("smart_migration.resume")
    org_id = auth.require_organization_id()
    try:
        run = _orch(db).resume(
            organization_id=org_id,
            migration_session_id=migration_session_id,
            actor_user_id=auth.user_id,
        )
        return ResumeOut(
            smart_run_id=run.id,
            status=run.status,
            progress_percent=float(run.progress_percent or 0),
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/cancel", response_model=CancelOut)
def cancel_migration(
    migration_session_id: str = Query(..., alias="migration_id"),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("smart_migration.cancel")
    org_id = auth.require_organization_id()
    try:
        run = _orch(db).cancel(
            organization_id=org_id,
            migration_session_id=migration_session_id,
            actor_user_id=auth.user_id,
        )
        return CancelOut(smart_run_id=run.id, status=run.status)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/retry_failed", response_model=RetryFailedOut)
def retry_failed(
    migration_session_id: str = Query(..., alias="migration_id"),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("smart_migration.run")
    org_id = auth.require_organization_id()
    try:
        run = _orch(db).retry_failed(
            organization_id=org_id,
            migration_session_id=migration_session_id,
            actor_user_id=auth.user_id,
        )
        return RetryFailedOut(smart_run_id=run.id, status=run.status)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/restart_batch", response_model=RestartBatchOut)
def restart_batch(
    body: RestartBatchIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("smart_migration.run")
    org_id = auth.require_organization_id()
    try:
        batch = _orch(db).restart_batch(
            organization_id=org_id,
            batch_id=body.batch_id,
            actor_user_id=auth.user_id,
            failed_only=body.failed_only,
        )
        return RestartBatchOut(
            batch_id=batch.id,
            status=batch.status,
            progress_percent=float(batch.progress_percent or 0),
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/cleanup")
def cleanup(
    body: CleanupIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("smart_migration.cleanup")
    org_id = auth.require_organization_id()
    try:
        return _orch(db).cleanup(
            organization_id=org_id,
            action=body.action,
            confirmed=body.confirmed,
            migration_session_id=body.migration_session_id,
            actor_user_id=auth.user_id,
        )
    except Exception as exc:
        raise _http(exc) from exc
