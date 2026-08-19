"""API Document Processing — /api/document-processing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.audit.audit_logger import AuditLogger
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.document_processing.exceptions import (
    DocumentProcessingError,
    ProcessingAccessDeniedError,
    ProcessingNotFoundError,
    ProcessingValidationError,
)
from app.document_processing.schemas import (
    ProcessingAttemptListOut,
    ProcessingAttemptOut,
    ProcessingJobCreate,
    ProcessingJobListOut,
    ProcessingJobOut,
    ProcessingStepListOut,
    ProcessingStepOut,
)
from app.document_processing.service import DocumentProcessingService

router = APIRouter(
    prefix="/document-processing",
    tags=["document-processing"],
    dependencies=[Depends(require_active_subscription)],
)


def _svc(db: Session) -> DocumentProcessingService:
    return DocumentProcessingService(db, audit_logger=AuditLogger(db))


def _http(exc: DocumentProcessingError) -> HTTPException:
    if isinstance(exc, ProcessingValidationError):
        return HTTPException(400, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, ProcessingAccessDeniedError):
        if exc.code == "permission_denied":
            return HTTPException(403, detail={"code": exc.code, "message": exc.message})
        return HTTPException(404, detail={"code": "not_found", "message": "Introuvable"})
    if isinstance(exc, ProcessingNotFoundError):
        return HTTPException(404, detail={"code": "not_found", "message": "Introuvable"})
    return HTTPException(500, detail={"code": "processing_error", "message": "Erreur processing"})


def _platform_jobs(auth: AuthContext) -> bool:
    perms = set(auth.permissions or [])
    return bool(perms & {"document_processing.jobs.manage", "*"})


@router.post("/jobs", response_model=ProcessingJobOut, status_code=201)
def create_job(
    body: ProcessingJobCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.jobs.create")
    org_id = auth.require_organization_id()
    try:
        job = _svc(db).create_job(
            organization_id=org_id,
            document_id=body.document_id,
            document_version_id=body.document_version_id,
            pipeline_key=body.pipeline_key,
            product=body.product,
            priority=body.priority,
            idempotency_key=body.idempotency_key,
            metadata=body.metadata,
            requested_by_user_id=auth.user.id if auth.user else None,
        )
    except DocumentProcessingError as exc:
        raise _http(exc) from exc
    return ProcessingJobOut.model_validate(job)


@router.get("/jobs", response_model=ProcessingJobListOut)
def list_jobs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    document_id: str | None = Query(None),
    pipeline_key: str | None = Query(None),
    product: str | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.jobs.read")
    platform = _platform_jobs(auth)
    org_id = None if platform else auth.require_organization_id()
    if not platform:
        org_id = auth.require_organization_id()
    items, total = _svc(db).list_jobs(
        organization_id=org_id,
        status=status,
        document_id=document_id,
        pipeline_key=pipeline_key,
        product=product,
        limit=limit,
        offset=offset,
        platform=platform,
    )
    return ProcessingJobListOut(
        items=[ProcessingJobOut.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/jobs/{job_id}", response_model=ProcessingJobOut)
def get_job(
    job_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.jobs.read")
    svc = _svc(db)
    try:
        if _platform_jobs(auth):
            job = svc.get_job_platform(job_id)
        else:
            job = svc.get_job_for_org(job_id, auth.require_organization_id())
    except DocumentProcessingError as exc:
        raise _http(exc) from exc
    return ProcessingJobOut.model_validate(job)


@router.get("/jobs/{job_id}/steps", response_model=ProcessingStepListOut)
def get_steps(
    job_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.jobs.read")
    svc = _svc(db)
    try:
        if _platform_jobs(auth):
            svc.get_job_platform(job_id)
        else:
            svc.get_job_for_org(job_id, auth.require_organization_id())
    except DocumentProcessingError as exc:
        raise _http(exc) from exc
    items = svc.list_steps(job_id)
    return ProcessingStepListOut(
        items=[ProcessingStepOut.model_validate(i) for i in items], total=len(items)
    )


@router.get("/jobs/{job_id}/attempts", response_model=ProcessingAttemptListOut)
def get_attempts(
    job_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.jobs.read")
    svc = _svc(db)
    try:
        if _platform_jobs(auth):
            svc.get_job_platform(job_id)
        else:
            svc.get_job_for_org(job_id, auth.require_organization_id())
    except DocumentProcessingError as exc:
        raise _http(exc) from exc
    items = svc.list_attempts(job_id)
    return ProcessingAttemptListOut(
        items=[ProcessingAttemptOut.model_validate(i) for i in items], total=len(items)
    )


@router.post("/jobs/{job_id}/cancel", response_model=ProcessingJobOut)
def cancel_job(
    job_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.jobs.cancel")
    platform = _platform_jobs(auth)
    org_id = 0 if platform else auth.require_organization_id()
    try:
        job = _svc(db).request_cancel(
            job_id,
            org_id,
            actor_user_id=auth.user.id if auth.user else None,
            platform=platform,
        )
    except DocumentProcessingError as exc:
        raise _http(exc) from exc
    return ProcessingJobOut.model_validate(job)


@router.post("/jobs/{job_id}/retry", response_model=ProcessingJobOut)
def retry_job(
    job_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.jobs.retry")
    platform = _platform_jobs(auth)
    org_id = 0 if platform else auth.require_organization_id()
    try:
        job = _svc(db).request_retry(
            job_id,
            org_id,
            actor_user_id=auth.user.id if auth.user else None,
            platform=platform,
        )
    except DocumentProcessingError as exc:
        raise _http(exc) from exc
    return ProcessingJobOut.model_validate(job)


# --- Classification RC2.5.2 ---


def _cls_svc(db: Session):
    from app.document_processing.classification.service import DocumentClassificationService

    return DocumentClassificationService(db, audit_logger=AuditLogger(db))


def _cls_http(exc: Exception):
    from app.document_processing.classification.exceptions import (
        ClassificationAccessDeniedError,
        ClassificationNotFoundError,
        ClassificationValidationError,
    )

    if isinstance(exc, ClassificationValidationError):
        return HTTPException(400, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, ClassificationAccessDeniedError):
        return HTTPException(404, detail={"code": "not_found", "message": "Introuvable"})
    if isinstance(exc, ClassificationNotFoundError):
        return HTTPException(404, detail={"code": "not_found", "message": "Introuvable"})
    return HTTPException(500, detail={"code": "classification_error", "message": "Erreur"})


def _platform_classifications(auth: AuthContext) -> bool:
    perms = set(auth.permissions or [])
    return bool(perms & {"document_processing.jobs.manage", "document_processing.classifications.review", "*"})


@router.get("/taxonomy")
def get_taxonomy(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require_any(
        [
            "document_processing.taxonomy.read",
            "document_processing.classifications.read",
            "document_processing.jobs.read",
            "*",
        ]
    )
    items = _cls_svc(db).taxonomy()
    return {"items": items}


@router.get("/classifications")
def list_classifications(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    document_id: str | None = Query(None),
    version_id: str | None = Query(None),
    predicted_type: str | None = Query(None),
    confirmed_type: str | None = Query(None),
    status: str | None = Query(None),
    requires_review: bool | None = Query(None),
    classifier_key: str | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.classifications.read")
    platform = _platform_classifications(auth)
    org_id = None if platform else auth.require_organization_id()
    items, total = _cls_svc(db).list_classifications(
        organization_id=org_id,
        document_id=document_id,
        version_id=version_id,
        predicted_type=predicted_type,
        confirmed_type=confirmed_type,
        status=status,
        requires_review=requires_review,
        classifier_key=classifier_key,
        limit=limit,
        offset=offset,
        platform=platform,
    )
    from app.document_processing.classification.schemas import ClassificationListOut, ClassificationOut

    return ClassificationListOut(
        items=[ClassificationOut.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/classifications/{classification_id}")
def get_classification(
    classification_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.classifications.read")
    svc = _cls_svc(db)
    try:
        if _platform_classifications(auth):
            row = svc.get_platform(classification_id)
        else:
            row = svc.get_for_org(classification_id, auth.require_organization_id())
    except Exception as exc:
        raise _cls_http(exc) from exc
    from app.document_processing.classification.schemas import ClassificationOut

    return ClassificationOut.model_validate(row)


@router.post("/classifications/{classification_id}/confirm")
def confirm_classification(
    classification_id: str,
    body: dict,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.classifications.review")
    from app.document_processing.classification.schemas import ClassificationConfirmIn, ClassificationOut

    payload = ClassificationConfirmIn.model_validate(body)
    platform = _platform_classifications(auth)
    org_id = 0 if platform else auth.require_organization_id()
    try:
        row = _cls_svc(db).confirm(
            classification_id,
            org_id,
            confirmed_type=payload.confirmed_type,
            actor_user_id=auth.user.id if auth.user else None,
            platform=platform,
        )
    except Exception as exc:
        raise _cls_http(exc) from exc
    return ClassificationOut.model_validate(row)


@router.post("/classifications/{classification_id}/reject")
def reject_classification(
    classification_id: str,
    body: dict | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.classifications.review")
    from app.document_processing.classification.schemas import ClassificationOut, ClassificationRejectIn

    payload = ClassificationRejectIn.model_validate(body or {})
    platform = _platform_classifications(auth)
    org_id = 0 if platform else auth.require_organization_id()
    try:
        row = _cls_svc(db).reject(
            classification_id,
            org_id,
            reason=payload.reason,
            actor_user_id=auth.user.id if auth.user else None,
            platform=platform,
        )
    except Exception as exc:
        raise _cls_http(exc) from exc
    return ClassificationOut.model_validate(row)


@router.post("/classifications/{classification_id}/reclassify", status_code=201)
def reclassify(
    classification_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.classifications.reclassify")
    platform = _platform_classifications(auth)
    org_id = 0 if platform else auth.require_organization_id()
    try:
        job = _cls_svc(db).request_reclassify(
            classification_id,
            org_id,
            actor_user_id=auth.user.id if auth.user else None,
            platform=platform,
            force=True,
        )
    except Exception as exc:
        raise _cls_http(exc) from exc
    return ProcessingJobOut.model_validate(job)


# --- OCR RC2.5.3 ---


def _ocr_svc(db: Session):
    from app.document_processing.ocr.service import DocumentOCRService

    return DocumentOCRService(db, audit_logger=AuditLogger(db))


def _ocr_http(exc: Exception):
    from app.document_processing.ocr.exceptions import (
        OCRAccessDeniedError,
        OCRNotFoundError,
        OCRValidationError,
    )

    if isinstance(exc, OCRValidationError):
        return HTTPException(400, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, (OCRAccessDeniedError, OCRNotFoundError)):
        return HTTPException(404, detail={"code": "not_found", "message": "Introuvable"})
    return HTTPException(500, detail={"code": "ocr_error", "message": "Erreur OCR"})


def _platform_ocr(auth: AuthContext) -> bool:
    perms = set(auth.permissions or [])
    return bool(perms & {"document_processing.jobs.manage", "*"})


@router.get("/ocr/providers")
def list_ocr_providers(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require_any(
        ["document_processing.ocr.providers.read", "document_processing.ocr.read", "*"]
    )
    return {"items": _ocr_svc(db).list_providers_public()}


@router.get("/ocr-results")
def list_ocr_results(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    document_id: str | None = Query(None),
    version_id: str | None = Query(None),
    status: str | None = Query(None),
    provider_key: str | None = Query(None),
    requires_review: bool | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.ocr.read")
    platform = _platform_ocr(auth)
    org_id = None if platform else auth.require_organization_id()
    items, total = _ocr_svc(db).list_results(
        organization_id=org_id,
        document_id=document_id,
        version_id=version_id,
        status=status,
        provider_key=provider_key,
        requires_review=requires_review,
        limit=limit,
        offset=offset,
        platform=platform,
    )
    from app.document_processing.ocr.schemas import OCRResultListOut, OCRResultOut

    return OCRResultListOut(
        items=[OCRResultOut.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/ocr-results/{ocr_result_id}")
def get_ocr_result(
    ocr_result_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.ocr.read")
    svc = _ocr_svc(db)
    try:
        row = (
            svc.get_platform(ocr_result_id)
            if _platform_ocr(auth)
            else svc.get_for_org(ocr_result_id, auth.require_organization_id())
        )
    except Exception as exc:
        raise _ocr_http(exc) from exc
    from app.document_processing.ocr.schemas import OCRResultOut

    return OCRResultOut.model_validate(row)


@router.get("/ocr-results/{ocr_result_id}/pages")
def get_ocr_pages(
    ocr_result_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.ocr.read")
    svc = _ocr_svc(db)
    try:
        if _platform_ocr(auth):
            svc.get_platform(ocr_result_id)
        else:
            svc.get_for_org(ocr_result_id, auth.require_organization_id())
    except Exception as exc:
        raise _ocr_http(exc) from exc
    pages = svc.list_pages(ocr_result_id)
    from app.document_processing.ocr.schemas import OCRPageListOut, OCRPageOut

    return OCRPageListOut(items=[OCRPageOut.model_validate(p) for p in pages], total=len(pages))


@router.get("/ocr-results/{ocr_result_id}/text")
def get_ocr_text(
    ocr_result_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.ocr.text.read")
    from fastapi.responses import Response

    svc = _ocr_svc(db)
    perms = set(auth.permissions or [])
    try:
        if "*" in perms or "document_processing.jobs.manage" in perms:
            data, _row = svc.open_text(
                ocr_result_id,
                0,
                platform=True,
                actor_user_id=auth.user.id if auth.user else None,
            )
        else:
            data, _row = svc.open_text(
                ocr_result_id,
                auth.require_organization_id(),
                platform=False,
                actor_user_id=auth.user.id if auth.user else None,
            )
    except Exception as exc:
        raise _ocr_http(exc) from exc
    return Response(
        content=data,
        media_type="application/json",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/ocr-results/{ocr_result_id}/retry", status_code=201)
def retry_ocr(
    ocr_result_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.ocr.retry")
    platform = _platform_ocr(auth)
    org_id = 0 if platform else auth.require_organization_id()
    try:
        job = _ocr_svc(db).request_retry(
            ocr_result_id,
            org_id,
            actor_user_id=auth.user.id if auth.user else None,
            platform=platform,
            force=True,
        )
    except Exception as exc:
        raise _ocr_http(exc) from exc
    return ProcessingJobOut.model_validate(job)


@router.post("/ocr-results/{ocr_result_id}/reject")
def reject_ocr(
    ocr_result_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.ocr.reject")
    platform = _platform_ocr(auth)
    org_id = 0 if platform else auth.require_organization_id()
    try:
        row = _ocr_svc(db).reject(ocr_result_id, org_id, platform=platform)
    except Exception as exc:
        raise _ocr_http(exc) from exc
    from app.document_processing.ocr.schemas import OCRResultOut

    return OCRResultOut.model_validate(row)

def _extr_svc(db: Session):
    from app.document_processing.extraction.service import DocumentExtractionService

    return DocumentExtractionService(db)


def _extr_http(exc: Exception):
    from app.document_processing.extraction.exceptions import (
        ExtractionAccessDeniedError,
        ExtractionNotFoundError,
        ExtractionValidationError,
    )

    if isinstance(exc, ExtractionNotFoundError):
        return HTTPException(status_code=404, detail=exc.message)
    if isinstance(exc, ExtractionAccessDeniedError):
        return HTTPException(status_code=403, detail=exc.message)
    if isinstance(exc, ExtractionValidationError):
        return HTTPException(status_code=400, detail=exc.message)
    return HTTPException(status_code=400, detail='extraction_error')


def _platform_extr(auth: AuthContext) -> bool:
    perms = set(auth.permissions or [])
    return bool(perms & {'document_processing.jobs.manage', '*'})


@router.get('/extraction-schemas')
def list_extraction_schemas(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require_any(
        ['document_processing.extraction_schemas.read', 'document_processing.extractions.read', '*']
    )
    return {'items': _extr_svc(db).list_schemas_public()}


@router.get('/extraction-providers')
def list_extraction_providers(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require_any(
        [
            'document_processing.extraction_providers.read',
            'document_processing.extractions.read',
            '*',
        ]
    )
    return {'items': _extr_svc(db).list_providers_public()}


@router.get('/extractions')
def list_extractions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    document_id: str | None = Query(None),
    version_id: str | None = Query(None),
    ocr_result_id: str | None = Query(None),
    schema_key: str | None = Query(None),
    provider_key: str | None = Query(None),
    status: str | None = Query(None),
    requires_review: bool | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require('document_processing.extractions.read')
    platform = _platform_extr(auth)
    org_id = None if platform else auth.require_organization_id()
    items, total = _extr_svc(db).list_results(
        organization_id=org_id,
        document_id=document_id,
        version_id=version_id,
        ocr_result_id=ocr_result_id,
        schema_key=schema_key,
        provider_key=provider_key,
        status=status,
        requires_review=requires_review,
        limit=limit,
        offset=offset,
        platform=platform,
    )
    from app.document_processing.extraction.schemas import ExtractionResultListOut, ExtractionResultOut

    return ExtractionResultListOut(
        items=[ExtractionResultOut.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get('/extractions/{extraction_id}')
def get_extraction(
    extraction_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require('document_processing.extractions.read')
    svc = _extr_svc(db)
    try:
        row = (
            svc.get_platform(extraction_id)
            if _platform_extr(auth)
            else svc.get_for_org(extraction_id, auth.require_organization_id())
        )
    except Exception as exc:
        raise _extr_http(exc) from exc
    from app.document_processing.extraction.schemas import ExtractionResultOut

    return ExtractionResultOut.model_validate(row)


@router.get('/extractions/{extraction_id}/fields')
def get_extraction_fields(
    extraction_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require('document_processing.extractions.read')
    svc = _extr_svc(db)
    try:
        if _platform_extr(auth):
            svc.get_platform(extraction_id)
        else:
            svc.get_for_org(extraction_id, auth.require_organization_id())
    except Exception as exc:
        raise _extr_http(exc) from exc
    fields = svc.list_fields(extraction_id)
    from app.document_processing.extraction.schemas import ExtractedFieldListOut, ExtractedFieldOut

    return ExtractedFieldListOut(
        items=[ExtractedFieldOut.model_validate(f) for f in fields], total=len(fields)
    )


@router.get('/extractions/{extraction_id}/content')
def get_extraction_content(
    extraction_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require('document_processing.extractions.content.read')
    from fastapi.responses import Response

    svc = _extr_svc(db)
    perms = set(auth.permissions or [])
    try:
        if '*' in perms or 'document_processing.jobs.manage' in perms:
            data, _row = svc.open_content(
                extraction_id,
                0,
                platform=True,
                actor_user_id=auth.user.id if auth.user else None,
            )
        else:
            data, _row = svc.open_content(
                extraction_id,
                auth.require_organization_id(),
                platform=False,
                actor_user_id=auth.user.id if auth.user else None,
            )
    except Exception as exc:
        raise _extr_http(exc) from exc
    return Response(
        content=data,
        media_type='application/json',
        headers={
            'X-Content-Type-Options': 'nosniff',
            'Cache-Control': 'private, no-store',
        },
    )


@router.post('/extractions/{extraction_id}/confirm')
def confirm_extraction(
    extraction_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require('document_processing.extractions.review')
    platform = _platform_extr(auth)
    org_id = 0 if platform else auth.require_organization_id()
    try:
        row = _extr_svc(db).confirm(
            extraction_id,
            org_id,
            actor_user_id=auth.user.id if auth.user else None,
            platform=platform,
        )
    except Exception as exc:
        raise _extr_http(exc) from exc
    from app.document_processing.extraction.schemas import ExtractionResultOut

    return ExtractionResultOut.model_validate(row)


@router.post('/extractions/{extraction_id}/reject')
def reject_extraction(
    extraction_id: str,
    body: dict | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require('document_processing.extractions.review')
    platform = _platform_extr(auth)
    org_id = 0 if platform else auth.require_organization_id()
    reason = (body or {}).get('reason') if isinstance(body, dict) else None
    try:
        row = _extr_svc(db).reject(
            extraction_id,
            org_id,
            reason=reason,
            actor_user_id=auth.user.id if auth.user else None,
            platform=platform,
        )
    except Exception as exc:
        raise _extr_http(exc) from exc
    from app.document_processing.extraction.schemas import ExtractionResultOut

    return ExtractionResultOut.model_validate(row)


@router.post('/extractions/{extraction_id}/correct')
def correct_extraction(
    extraction_id: str,
    body: dict,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require('document_processing.extractions.correct')
    platform = _platform_extr(auth)
    org_id = 0 if platform else auth.require_organization_id()
    patch = body.get('patch') if isinstance(body, dict) else {}
    reason = body.get('reason') if isinstance(body, dict) else None
    try:
        row = _extr_svc(db).correct(
            extraction_id,
            org_id,
            patch=patch or {},
            actor_user_id=auth.user.id if auth.user else None,
            reason=reason,
            platform=platform,
        )
    except Exception as exc:
        raise _extr_http(exc) from exc
    from app.document_processing.extraction.schemas import ExtractionResultOut

    return ExtractionResultOut.model_validate(row)


@router.post('/extractions/{extraction_id}/reextract', status_code=201)
def reextract(
    extraction_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require('document_processing.extractions.retry')
    platform = _platform_extr(auth)
    org_id = 0 if platform else auth.require_organization_id()
    try:
        job = _extr_svc(db).request_reextract(
            extraction_id,
            org_id,
            actor_user_id=auth.user.id if auth.user else None,
            platform=platform,
            force=True,
        )
    except Exception as exc:
        raise _extr_http(exc) from exc
    return ProcessingJobOut.model_validate(job)


# --- Business Validation RC2.5.5 ---


def _bv_svc(db: Session):
    from app.document_processing.validation.service import DocumentBusinessValidationService

    return DocumentBusinessValidationService(db, audit_logger=AuditLogger(db))


def _bv_http(exc: Exception) -> HTTPException:
    from app.document_processing.validation.exceptions import (
        BusinessValidationAccessDeniedError,
        BusinessValidationNotFoundError,
        BusinessValidationValidationError,
    )

    if isinstance(exc, BusinessValidationNotFoundError):
        return HTTPException(status_code=404, detail=exc.message)
    if isinstance(exc, BusinessValidationAccessDeniedError):
        return HTTPException(status_code=403, detail=exc.message)
    if isinstance(exc, BusinessValidationValidationError):
        return HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})
    return HTTPException(status_code=400, detail="business_validation_error")


@router.get("/business-validations")
def list_business_validations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    document_id: str | None = Query(None),
    version_id: str | None = Query(None),
    extraction_result_id: str | None = Query(None),
    status: str | None = Query(None),
    requires_review: bool | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.business_validations.read")
    platform = _platform_extr(auth)
    org_id = None if platform else auth.require_organization_id()
    items, total = _bv_svc(db).list_results(
        organization_id=org_id,
        document_id=document_id,
        version_id=version_id,
        extraction_result_id=extraction_result_id,
        status=status,
        requires_review=requires_review,
        limit=limit,
        offset=offset,
        platform=platform,
    )
    from app.document_processing.validation.schemas import BusinessValidationListOut, BusinessValidationOut

    return BusinessValidationListOut(
        items=[BusinessValidationOut.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/business-validations/{validation_id}")
def get_business_validation(
    validation_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.business_validations.read")
    svc = _bv_svc(db)
    try:
        row = (
            svc.get_platform(validation_id)
            if _platform_extr(auth)
            else svc.get_for_org(validation_id, auth.require_organization_id())
        )
    except Exception as exc:
        raise _bv_http(exc) from exc
    from app.document_processing.validation.schemas import BusinessValidationOut

    return BusinessValidationOut.model_validate(row)


@router.get("/business-validations/{validation_id}/issues")
def list_business_validation_issues(
    validation_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.business_validations.read")
    svc = _bv_svc(db)
    try:
        if _platform_extr(auth):
            svc.get_platform(validation_id)
        else:
            svc.get_for_org(validation_id, auth.require_organization_id())
    except Exception as exc:
        raise _bv_http(exc) from exc
    issues = svc.list_issues(validation_id)
    from app.document_processing.validation.schemas import ValidationIssueListOut, ValidationIssueOut

    return ValidationIssueListOut(
        items=[ValidationIssueOut.model_validate(i) for i in issues],
        total=len(issues),
    )


@router.post("/business-validations", status_code=201)
def create_business_validation(
    body: dict,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.business_validations.create")
    org_id = auth.require_organization_id()
    document_id = body.get("document_id") if isinstance(body, dict) else None
    version_id = body.get("document_version_id") if isinstance(body, dict) else None
    if not document_id:
        raise HTTPException(status_code=400, detail="document_id required")
    try:
        job = _bv_svc(db).request_validate(
            organization_id=org_id,
            document_id=document_id,
            document_version_id=version_id,
            actor_user_id=auth.user.id if auth.user else None,
            force=bool((body or {}).get("force")),
        )
    except Exception as exc:
        raise _bv_http(exc) from exc
    return ProcessingJobOut.model_validate(job)


@router.post("/business-validations/{validation_id}/confirm")
def confirm_business_validation(
    validation_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.business_validations.confirm")
    platform = _platform_extr(auth)
    org_id = 0 if platform else auth.require_organization_id()
    try:
        row = _bv_svc(db).confirm(
            validation_id,
            org_id,
            actor_user_id=auth.user.id if auth.user else None,
            platform=platform,
        )
    except Exception as exc:
        raise _bv_http(exc) from exc
    from app.document_processing.validation.schemas import BusinessValidationOut

    return BusinessValidationOut.model_validate(row)


@router.post("/business-validations/{validation_id}/revalidate", status_code=201)
def revalidate_business_validation(
    validation_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.business_validations.create")
    platform = _platform_extr(auth)
    org_id = 0 if platform else auth.require_organization_id()
    try:
        job = _bv_svc(db).request_revalidate(
            validation_id,
            org_id,
            actor_user_id=auth.user.id if auth.user else None,
            platform=platform,
        )
    except Exception as exc:
        raise _bv_http(exc) from exc
    return ProcessingJobOut.model_validate(job)


@router.post("/business-validations/{validation_id}/issues/{issue_id}/resolve")
def resolve_business_validation_issue(
    validation_id: str,
    issue_id: str,
    body: dict,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_processing.business_validations.review")
    platform = _platform_extr(auth)
    org_id = 0 if platform else auth.require_organization_id()
    resolution_type = (body or {}).get("resolution_type") if isinstance(body, dict) else None
    if not resolution_type:
        raise HTTPException(status_code=400, detail="resolution_type required")
    try:
        issue = _bv_svc(db).resolve_issue(
            validation_id,
            issue_id,
            org_id,
            resolution_type=resolution_type,
            actor_user_id=auth.user.id if auth.user else None,
            platform=platform,
        )
    except Exception as exc:
        raise _bv_http(exc) from exc
    from app.document_processing.validation.schemas import ValidationIssueOut

    return ValidationIssueOut.model_validate(issue)
