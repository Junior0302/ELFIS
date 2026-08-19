"""Routes HTTP Document Intake — /api/document-intake."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.document_intake.enums import IntakeOrigin
from app.document_intake.exceptions import (
    DocumentIntakeAccessDeniedError,
    DocumentIntakeConflictError,
    DocumentIntakeError,
    DocumentIntakeNotFoundError,
    DocumentIntakeQuotaError,
    DocumentIntakeValidationError,
)
from app.document_intake.schemas import (
    BatchUploadResultOut,
    FormatCatalogOut,
    IntakeItemListOut,
    IntakeItemOut,
    LifecycleEntryOut,
    LifecycleListOut,
    UploadAnalyticsOut,
    UploadResultOut,
    UploadSessionCreateIn,
    UploadSessionListOut,
    UploadSessionOut,
)
from app.document_intake.service import DocumentIntakeService
from app.document_intake.upload_session_service import UploadSessionService

router = APIRouter(
    prefix="/document-intake",
    tags=["document-intake"],
    dependencies=[Depends(require_active_subscription)],
)


def _svc(db: Session) -> DocumentIntakeService:
    return DocumentIntakeService(db)


def _upload_svc(db: Session) -> UploadSessionService:
    return UploadSessionService(db)


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, DocumentIntakeNotFoundError):
        return HTTPException(status_code=404, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, DocumentIntakeAccessDeniedError):
        return HTTPException(status_code=403, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, DocumentIntakeQuotaError):
        return HTTPException(status_code=413, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, DocumentIntakeConflictError):
        return HTTPException(status_code=409, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, DocumentIntakeValidationError):
        return HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, DocumentIntakeError):
        return HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})
    return HTTPException(
        status_code=400, detail={"code": "document_intake_error", "message": "Erreur intake"}
    )


@router.get("/formats", response_model=FormatCatalogOut)
def format_catalog(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_intake.read")
    auth.require_organization_id()
    return FormatCatalogOut(items=_svc(db).get_format_catalog())


@router.get("/items", response_model=IntakeItemListOut)
def list_items(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    migration_session_id: str | None = Query(None),
    upload_session_id: str | None = Query(None),
    batch_id: str | None = Query(None),
    status: str | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_intake.read")
    org_id = auth.require_organization_id()
    items, total, summary = _svc(db).list_items(
        organization_id=org_id,
        migration_session_id=migration_session_id,
        upload_session_id=upload_session_id,
        batch_id=batch_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return IntakeItemListOut(
        items=[IntakeItemOut.from_orm_item(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
        summary=summary,
    )


@router.get("/items/{item_id}", response_model=IntakeItemOut)
def get_item(
    item_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_intake.read")
    org_id = auth.require_organization_id()
    try:
        return IntakeItemOut.from_orm_item(_svc(db).get_for_org(item_id, org_id))
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/items/{item_id}/lifecycle", response_model=LifecycleListOut)
def get_item_lifecycle(
    item_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_intake.read")
    org_id = auth.require_organization_id()
    try:
        entries = _svc(db).list_lifecycle(item_id, org_id)
        return LifecycleListOut(
            items=[LifecycleEntryOut.model_validate(e) for e in entries]
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/uploads", response_model=UploadResultOut, status_code=201)
async def upload_one(
    file: UploadFile = File(...),
    migration_session_id: str | None = Form(None),
    upload_session_id: str | None = Form(None),
    relative_path: str | None = Form(None),
    client_upload_id: str | None = Form(None),
    idempotency_key: str | None = Form(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_intake.upload")
    org_id = auth.require_organization_id()
    try:
        content = await file.read()
        row = _svc(db).ingest_bytes(
            organization_id=org_id,
            filename=file.filename or "unnamed",
            content=content,
            actor_user_id=auth.user_id,
            declared_mime=file.content_type,
            migration_session_id=migration_session_id,
            relative_path=relative_path,
            upload_session_id=upload_session_id,
            client_upload_id=client_upload_id,
            idempotency_key=idempotency_key,
            origin=IntakeOrigin.MIGRATION.value if migration_session_id else IntakeOrigin.API.value,
        )
        return UploadResultOut(item=IntakeItemOut.from_orm_item(row), batch_id=row.batch_id)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/uploads/batch", response_model=BatchUploadResultOut, status_code=201)
async def upload_batch(
    files: list[UploadFile] = File(...),
    migration_session_id: str | None = Form(None),
    upload_session_id: str | None = Form(None),
    relative_paths: str | None = Form(None),
    idempotency_keys: str | None = Form(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """relative_paths / idempotency_keys: JSON arrays alignés sur files."""
    auth.require("document_intake.upload")
    org_id = auth.require_organization_id()
    paths: list[str | None] = []
    keys: list[str | None] = []
    import json

    if relative_paths:
        try:
            parsed = json.loads(relative_paths)
            if isinstance(parsed, list):
                paths = [str(p) if p is not None else None for p in parsed]
        except Exception:
            paths = []
    if idempotency_keys:
        try:
            parsed = json.loads(idempotency_keys)
            if isinstance(parsed, list):
                keys = [str(p) if p is not None else None for p in parsed]
        except Exception:
            keys = []
    payload = []
    for idx, f in enumerate(files):
        content = await f.read()
        payload.append(
            {
                "filename": f.filename or "unnamed",
                "content": content,
                "declared_mime": f.content_type,
                "relative_path": paths[idx] if idx < len(paths) else None,
                "idempotency_key": keys[idx] if idx < len(keys) else None,
            }
        )
    try:
        batch_id, items, stats = _svc(db).ingest_batch(
            organization_id=org_id,
            files=payload,
            actor_user_id=auth.user_id,
            migration_session_id=migration_session_id,
            upload_session_id=upload_session_id,
            origin=IntakeOrigin.FOLDER.value,
        )
        return BatchUploadResultOut(
            batch_id=batch_id,
            items=[IntakeItemOut.from_orm_item(i) for i in items],
            accepted=stats["accepted"],
            rejected=stats["rejected"],
            duplicates=stats["duplicates"],
            quarantined=stats["quarantined"],
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/items/{item_id}/cancel", response_model=IntakeItemOut)
def cancel_item(
    item_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_intake.cancel")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).cancel_item(item_id, org_id, actor_user_id=auth.user_id)
        return IntakeItemOut.from_orm_item(row)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/upload-sessions", response_model=UploadSessionOut, status_code=201)
def create_upload_session(
    body: UploadSessionCreateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_intake.upload")
    org_id = auth.require_organization_id()
    try:
        row = _upload_svc(db).create_session(
            organization_id=org_id,
            migration_session_id=body.migration_session_id,
            created_by_user_id=auth.user_id,
            source_type=body.source_type,
            expected_file_count=body.expected_file_count,
            expected_total_bytes=body.expected_total_bytes,
            display_label=body.display_label,
            metadata=body.metadata,
        )
        return UploadSessionOut.from_orm_session(row)
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/upload-sessions", response_model=UploadSessionListOut)
def list_upload_sessions(
    migration_session_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_intake.read")
    org_id = auth.require_organization_id()
    rows, total = _upload_svc(db).list_sessions(
        organization_id=org_id,
        migration_session_id=migration_session_id,
        limit=limit,
        offset=offset,
    )
    return UploadSessionListOut(
        items=[UploadSessionOut.from_orm_session(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/upload-sessions/{session_id}", response_model=UploadSessionOut)
def get_upload_session(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_intake.read")
    org_id = auth.require_organization_id()
    try:
        return UploadSessionOut.from_orm_session(
            _upload_svc(db).get_session(session_id, org_id)
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/upload-sessions/{session_id}/pause", response_model=UploadSessionOut)
def pause_upload_session(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_intake.upload")
    org_id = auth.require_organization_id()
    try:
        return UploadSessionOut.from_orm_session(
            _upload_svc(db).pause(session_id, org_id, actor_user_id=auth.user_id)
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/upload-sessions/{session_id}/resume", response_model=UploadSessionOut)
def resume_upload_session(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_intake.upload")
    org_id = auth.require_organization_id()
    try:
        return UploadSessionOut.from_orm_session(
            _upload_svc(db).resume(session_id, org_id, actor_user_id=auth.user_id)
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/upload-sessions/{session_id}/cancel", response_model=UploadSessionOut)
def cancel_upload_session(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_intake.cancel")
    org_id = auth.require_organization_id()
    try:
        return UploadSessionOut.from_orm_session(
            _upload_svc(db).cancel(session_id, org_id, actor_user_id=auth.user_id)
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/upload-sessions/{session_id}/analytics", response_model=UploadAnalyticsOut)
def upload_session_analytics(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_intake.read")
    org_id = auth.require_organization_id()
    try:
        from app.document_intake.analytics_service import UploadAnalyticsService

        sess = _upload_svc(db).get_session(session_id, org_id)
        data = UploadAnalyticsService(db).get_for_upload_session(sess)
        return UploadAnalyticsOut.model_validate(data)
    except Exception as exc:
        raise _http(exc) from exc
