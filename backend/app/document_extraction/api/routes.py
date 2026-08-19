"""Routes HTTP Document Extraction — /api/document-extraction."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.document_extraction.exceptions import (
    DocumentExtractionConflictError,
    DocumentExtractionError,
    DocumentExtractionIneligibleError,
    DocumentExtractionNotFoundError,
    DocumentExtractionQuotaError,
)
from app.document_extraction.schemas import (
    ExtractBatchOut,
    ExtractRequestIn,
    ExtractionFieldsOut,
    ExtractionListOut,
    ExtractionOut,
    ExtractionProvenanceOut,
    ExtractionWarningsOut,
)
from app.document_extraction.service import DocumentExtractionService

router = APIRouter(
    prefix="/document-extraction",
    tags=["document-extraction"],
    dependencies=[Depends(require_active_subscription)],
)


def _svc(db: Session) -> DocumentExtractionService:
    return DocumentExtractionService(db)


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, DocumentExtractionNotFoundError):
        return HTTPException(status_code=404, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, DocumentExtractionIneligibleError):
        return HTTPException(status_code=409, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, DocumentExtractionQuotaError):
        return HTTPException(status_code=429, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, DocumentExtractionConflictError):
        return HTTPException(status_code=409, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, DocumentExtractionError):
        return HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})
    return HTTPException(
        status_code=400,
        detail={"code": "document_extraction_error", "message": "Erreur extraction"},
    )


def _sensitive(auth: AuthContext) -> bool:
    try:
        auth.require("document_extraction.view_sensitive")
        return True
    except Exception:
        return False


@router.post("/documents/{document_id}/extract", response_model=ExtractionOut, status_code=201)
def start_extract(
    document_id: str,
    body: ExtractRequestIn | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_extraction.run")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).start_extraction(
            document_id,
            org_id,
            actor_user_id=auth.user_id,
            force_reextract=bool(body.force_reextract) if body else False,
            schema_name=body.schema_name if body else None,
            sync=True,
        )
        return ExtractionOut.from_orm_row(row, include_sensitive=_sensitive(auth))
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/documents/{document_id}/extractions", response_model=ExtractionListOut)
def list_document_extractions(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_extraction.read")
    org_id = auth.require_organization_id()
    try:
        rows = _svc(db).list_for_document(document_id, org_id)
        return ExtractionListOut(
            items=[ExtractionOut.from_orm_row(r) for r in rows],
            total=len(rows),
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/sessions/{migration_session_id}/extractions", response_model=ExtractionListOut)
def list_session_extractions(
    migration_session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_extraction.read")
    org_id = auth.require_organization_id()
    rows = _svc(db).list_for_session(
        organization_id=org_id, migration_session_id=migration_session_id
    )
    return ExtractionListOut(
        items=[ExtractionOut.from_orm_row(r) for r in rows],
        total=len(rows),
    )


@router.post(
    "/sessions/{migration_session_id}/extract",
    response_model=ExtractBatchOut,
    status_code=201,
)
def extract_session(
    migration_session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_extraction.run")
    org_id = auth.require_organization_id()
    try:
        result = _svc(db).extract_migration_session(
            organization_id=org_id,
            migration_session_id=migration_session_id,
            actor_user_id=auth.user_id,
        )
        return ExtractBatchOut(
            extracted=result["extracted"],
            errors=result["errors"],
            items=[
                ExtractionOut.from_orm_row(r, include_sensitive=_sensitive(auth))
                for r in result["items"]
            ],
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/extractions/{extraction_id}", response_model=ExtractionOut)
def get_extraction(
    extraction_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_extraction.read")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).get_extraction(extraction_id, org_id)
        return ExtractionOut.from_orm_row(row, include_sensitive=_sensitive(auth))
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/extractions/{extraction_id}/status", response_model=ExtractionOut)
def get_status(
    extraction_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    return get_extraction(extraction_id, auth, db)


@router.get("/extractions/{extraction_id}/fields", response_model=ExtractionFieldsOut)
def get_fields(
    extraction_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_extraction.read")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).get_extraction(extraction_id, org_id)
        prov = row.field_provenance or {}
        low = [
            k
            for k, v in prov.items()
            if isinstance(v, dict) and float(v.get("confidence") or 1) < 0.70
        ]
        return ExtractionFieldsOut(fields=row.structured_data or {}, low_confidence=low)
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/extractions/{extraction_id}/warnings", response_model=ExtractionWarningsOut)
def get_warnings(
    extraction_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_extraction.read")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).get_extraction(extraction_id, org_id)
        return ExtractionWarningsOut(
            warnings=list(row.warnings_json or []),
            errors=list(row.errors_json or []),
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/extractions/{extraction_id}/provenance", response_model=ExtractionProvenanceOut)
def get_provenance(
    extraction_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_extraction.read")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).get_extraction(extraction_id, org_id)
        return ExtractionProvenanceOut(provenance=dict(row.field_provenance or {}))
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/extractions/{extraction_id}/retry", response_model=ExtractionOut)
def retry_extraction(
    extraction_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_extraction.retry")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).retry_extraction(
            extraction_id, org_id, actor_user_id=auth.user_id
        )
        return ExtractionOut.from_orm_row(row)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/extractions/{extraction_id}/cancel", response_model=ExtractionOut)
def cancel_extraction(
    extraction_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_extraction.cancel")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).cancel_extraction(
            extraction_id, org_id, actor_user_id=auth.user_id
        )
        return ExtractionOut.from_orm_row(row)
    except Exception as exc:
        raise _http(exc) from exc
