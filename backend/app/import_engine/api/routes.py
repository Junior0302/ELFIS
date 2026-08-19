"""Routes HTTP Import Engine — /api/import."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.import_engine.exceptions import (
    ImportConflictError,
    ImportEngineError,
    ImportIdempotencyError,
    ImportNotFoundError,
    ImportStateError,
    ImportValidationError,
)
from app.import_engine.schemas import (
    ImportReportOut,
    ImportRunListOut,
    ImportRunOut,
    ReadyDocumentListOut,
    RollbackIn,
)
from app.import_engine.service import ImportEngineService

router = APIRouter(
    prefix="/import",
    tags=["import-engine"],
    dependencies=[Depends(require_active_subscription)],
)


def _svc(db: Session) -> ImportEngineService:
    return ImportEngineService(db)


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, ImportNotFoundError):
        return HTTPException(
            status_code=404, detail={"code": exc.code, "message": exc.message}
        )
    if isinstance(exc, (ImportConflictError, ImportIdempotencyError, ImportStateError)):
        return HTTPException(
            status_code=409, detail={"code": exc.code, "message": exc.message}
        )
    if isinstance(exc, ImportValidationError):
        return HTTPException(
            status_code=400, detail={"code": exc.code, "message": exc.message}
        )
    if isinstance(exc, ImportEngineError):
        return HTTPException(
            status_code=400, detail={"code": exc.code, "message": exc.message}
        )
    return HTTPException(
        status_code=400,
        detail={"code": "import_error", "message": "Erreur d'import"},
    )


@router.get("/ready", response_model=ReadyDocumentListOut)
def list_ready(
    migration_session_id: str | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("import.read")
    org_id = auth.require_organization_id()
    items = _svc(db).list_ready_documents(
        organization_id=org_id, migration_session_id=migration_session_id
    )
    return ReadyDocumentListOut(items=items, total=len(items))


@router.post("/documents/{document_id}/import", response_model=ImportRunOut, status_code=201)
def import_document(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("import.run")
    org_id = auth.require_organization_id()
    try:
        run = _svc(db).import_document(
            organization_id=org_id,
            document_id=document_id,
            actor_user_id=auth.user_id,
        )
        return ImportRunOut.from_orm_row(run)
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/imports", response_model=ImportRunListOut)
def list_imports(
    migration_session_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("import.read")
    org_id = auth.require_organization_id()
    items, total = _svc(db).list_imports(
        organization_id=org_id,
        migration_session_id=migration_session_id,
        limit=limit,
        offset=offset,
    )
    return ImportRunListOut(
        items=[ImportRunOut.from_orm_row(r) for r in items], total=total
    )


@router.get("/imports/{import_id}", response_model=ImportRunOut)
def get_import(
    import_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("import.read")
    org_id = auth.require_organization_id()
    try:
        run = _svc(db).get_import(organization_id=org_id, import_id=import_id)
        return ImportRunOut.from_orm_row(run)
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/imports/{import_id}/report", response_model=ImportReportOut)
def get_report(
    import_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("import.report")
    org_id = auth.require_organization_id()
    try:
        report = _svc(db).get_report(organization_id=org_id, import_id=import_id)
        return ImportReportOut.from_orm_row(report)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/imports/{import_id}/retry", response_model=ImportRunOut)
def retry_import(
    import_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("import.run")
    org_id = auth.require_organization_id()
    try:
        run = _svc(db).retry_import(
            organization_id=org_id,
            import_id=import_id,
            actor_user_id=auth.user_id,
        )
        return ImportRunOut.from_orm_row(run)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/imports/{import_id}/rollback", response_model=ImportRunOut)
def rollback_import(
    import_id: str,
    body: RollbackIn | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("import.rollback")
    org_id = auth.require_organization_id()
    try:
        run = _svc(db).rollback_import(
            organization_id=org_id,
            import_id=import_id,
            actor_user_id=auth.user_id,
            reason=(body.reason if body else None),
        )
        return ImportRunOut.from_orm_row(run)
    except Exception as exc:
        raise _http(exc) from exc
