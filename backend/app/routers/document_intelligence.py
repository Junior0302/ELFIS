"""Routes Document Intelligence — utilisateur + plateforme."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription, require_platform_admin
from app.document_intelligence.document_exceptions import (
    DocumentDisabledError,
    DocumentNotFoundError,
)
from app.document_intelligence.document_registry import bootstrap_extractors
from app.document_intelligence.document_repository import DocumentExtractionRepository
from app.document_intelligence.document_schemas import ExtractTextAccepted
from app.document_intelligence.document_service import DocumentIntelligenceService
from app.document_intelligence.document_types import ExtractionStatus
from app.jobs import bootstrap_job_handlers
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames
from app.models_saas import User
from app.models_vault import VaultDocument
import uuid

router = APIRouter(tags=["document-intelligence"])
platform_router = APIRouter(
    prefix="/platform",
    tags=["platform-document-intelligence"],
    dependencies=[Depends(require_platform_admin)],
)


def _load_vault_doc(db: Session, vault_document_id: str, organization_id: int) -> VaultDocument:
    doc = db.query(VaultDocument).filter(VaultDocument.id == vault_document_id).first()
    if not doc or doc.organization_id != organization_id:
        raise HTTPException(404, detail="Document introuvable")
    return doc


@router.post(
    "/documents/{vault_document_id}/extract-text",
    status_code=202,
    dependencies=[Depends(require_active_subscription)],
)
def extract_text(
    vault_document_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Enqueue extraction de texte via Job Queue. 202 Accepted."""
    bootstrap_extractors()
    bootstrap_job_handlers()
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    doc = _load_vault_doc(db, vault_document_id, org_id)
    version = int(doc.version or 1)
    svc = DocumentIntelligenceService(db)

    existing = DocumentExtractionRepository(db).find_for_document(
        organization_id=org_id,
        vault_document_id=vault_document_id,
        document_version=version,
    )
    if existing and existing.status in (
        ExtractionStatus.COMPLETED,
        ExtractionStatus.REQUIRES_OCR,
        ExtractionStatus.REQUIRES_REVIEW,
        ExtractionStatus.PROCESSING,
        ExtractionStatus.PENDING,
    ):
        return ExtractTextAccepted(
            extraction_id=existing.extraction_id,
            job_id=existing.job_id,
            status=existing.status,
            reused_existing_extraction=True,
        ).model_dump()

    pending = svc.get_or_create_pending(
        organization_id=org_id,
        vault_document_id=vault_document_id,
        document_version=version,
        user_id=auth.user.id,
    )
    idem = f"document-text:{org_id}:{vault_document_id}:{version}"
    try:
        job = JobService(db).enqueue(
            JobRequest(
                job_name=JobNames.VAULT_DOCUMENT_EXTRACT_TEXT,
                organization_id=org_id,
                user_id=auth.user.id,
                payload={
                    "vault_document_id": vault_document_id,
                    "document_version": version,
                    "idempotency_key": idem,
                },
                idempotency_key=idem,
                correlation_id=str(uuid.uuid4()),
            )
        )
    except DocumentDisabledError as exc:
        raise HTTPException(503, detail=exc.message) from None
    except Exception as exc:
        if "disabled" in str(exc).lower():
            raise HTTPException(503, detail="Document Intelligence désactivé") from None
        raise

    pending.job_id = job.job_id
    pending.idempotency_key = idem
    DocumentExtractionRepository(db).save(pending)

    return ExtractTextAccepted(
        extraction_id=pending.extraction_id,
        job_id=job.job_id,
        status=pending.status,
        reused_existing_extraction=False,
    ).model_dump()


@router.get(
    "/documents/{vault_document_id}/text-extraction",
    dependencies=[Depends(require_active_subscription)],
)
def get_text_extraction(
    vault_document_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    org_id = auth.require_organization_id()
    doc = _load_vault_doc(db, vault_document_id, org_id)
    row = DocumentExtractionRepository(db).find_for_document(
        organization_id=org_id,
        vault_document_id=vault_document_id,
        document_version=int(doc.version or 1),
    )
    if not row:
        raise HTTPException(404, detail="Extraction introuvable")
    return DocumentIntelligenceService(db).to_view(row).model_dump()


@router.get(
    "/documents/{vault_document_id}/text-preview",
    dependencies=[Depends(require_active_subscription)],
)
def get_text_preview(
    vault_document_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Preview limitée (2000 caractères) — tenant strict."""
    org_id = auth.require_organization_id()
    doc = _load_vault_doc(db, vault_document_id, org_id)
    row = DocumentExtractionRepository(db).find_for_document(
        organization_id=org_id,
        vault_document_id=vault_document_id,
        document_version=int(doc.version or 1),
    )
    if not row:
        raise HTTPException(404, detail="Extraction introuvable")
    svc = DocumentIntelligenceService(db)
    return {
        "extraction_id": row.extraction_id,
        "status": row.status,
        "preview": svc.text_preview(row, max_chars=2000),
        "text_length": row.text_length or 0,
    }


@platform_router.get("/document-extractions")
def platform_list_extractions(
    organization_id: int | None = None,
    status: str | None = None,
    extractor_name: str | None = None,
    requires_ocr: bool | None = None,
    requires_review: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    _ = admin
    bootstrap_extractors()
    rows, total = DocumentExtractionRepository(db).list_extractions(
        organization_id=organization_id,
        status=status,
        extractor_name=extractor_name,
        requires_ocr=requires_ocr,
        requires_review=requires_review,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": max(1, page),
        "page_size": min(100, max(1, page_size)),
        "extractions": [
            {
                "extraction_id": r.extraction_id,
                "organization_id": r.organization_id,
                "vault_document_id": r.vault_document_id,
                "document_version": r.document_version,
                "status": r.status,
                "extractor_name": r.extractor_name,
                "text_length": r.text_length or 0,
                "quality_score": float(r.quality_score) if r.quality_score is not None else None,
                "confidence": float(r.confidence) if r.confidence is not None else None,
                "requires_ocr": bool(r.requires_ocr),
                "requires_review": bool(r.requires_review),
                "created_at": r.created_at,
                "completed_at": r.completed_at,
            }
            for r in rows
        ],
    }


@platform_router.get("/document-extractions/{extraction_id}")
def platform_get_extraction(
    extraction_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    _ = admin
    try:
        row = DocumentIntelligenceService(db).get_extraction(extraction_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(404, detail=exc.message) from None
    preview = DocumentIntelligenceService(db).text_preview(row, max_chars=2000)
    view = DocumentIntelligenceService(db).to_view(row).model_dump()
    view.update(
        {
            "organization_id": row.organization_id,
            "vault_document_id": row.vault_document_id,
            "document_version": row.document_version,
            "mime_type": row.mime_type,
            "filename": row.filename,
            "file_size_bytes": row.file_size_bytes,
            "preview": preview,
            "last_error": row.last_error,
        }
    )
    return view
