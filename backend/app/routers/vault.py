"""Routes ELFIS Vault."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.schemas_vault import (
    VaultArchiveFormMeta,
    VaultArchiveStatus,
    VaultDocumentDetail,
    VaultDocumentListResponse,
    VaultDocumentResponse,
    VaultDocumentType,
    VaultDownloadUrlResponse,
    VaultSortBy,
    VaultSortOrder,
)
from app.services.vault.exceptions import (
    VaultAccessDeniedError,
    VaultDatabaseError,
    VaultDuplicateDocumentError,
    VaultFileTooLargeError,
    VaultInvalidFileError,
    VaultNotFoundError,
    VaultStorageError,
    VaultValidationError,
)
from app.services.vault.vault_access_service import (
    ACCESS_DENIED_MESSAGE,
    DOCUMENT_NOT_FOUND_MESSAGE,
    ORG_ACCESS_DENIED_MESSAGE,
)
from app.services.vault import vault_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/vault",
    tags=["vault"],
    dependencies=[Depends(require_active_subscription)],
)


def _parse_optional_date(value: str | None) -> date | None:
    if value is None or value.strip() == "":
        return None
    return date.fromisoformat(value.strip())


def _parse_optional_decimal(value: str | None) -> Decimal | None:
    if value is None or value.strip() == "":
        return None
    try:
        return Decimal(value.strip())
    except (InvalidOperation, ValueError) as exc:
        raise VaultInvalidFileError("Montant invalide") from exc


def _parse_optional_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    return int(value.strip())


def _require_user(auth: AuthContext):
    if auth.user is None:
        return None
    return auth.user


@router.post(
    "/documents/archive",
    response_model=VaultDocumentResponse,
    status_code=201,
)
async def archive_vault_document(
    file: UploadFile = File(...),
    tenant_id: int = Form(...),
    document_type: str = Form(...),
    document_number: str | None = Form(default=None),
    invoice_date: str | None = Form(default=None),
    due_date: str | None = Form(default=None),
    amount_ht: str | None = Form(default=None),
    amount_vat: str | None = Form(default=None),
    amount_ttc: str | None = Form(default=None),
    currency: str = Form(default="EUR"),
    customer_id: str | None = Form(default=None),
    supplier_id: str | None = Form(default=None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Archive un PDF dans le coffre-fort documentaire multi-tenant."""
    if auth.user is None:
        return JSONResponse(status_code=401, content={"detail": "Authentification requise"})

    # Isolation : tenant_id formulaire = organisation active du contexte (anti mass-assignment)
    try:
        active_org_id = auth.require_organization_id()
    except Exception:
        return JSONResponse(
            status_code=403,
            content={"detail": {"code": "organization_required", "message": "Organisation requise"}},
        )
    if int(tenant_id) != int(active_org_id):
        from app.security.security_audit import record_security_event
        from app.security.security_types import SecurityEventType

        record_security_event(
            db,
            event_type=SecurityEventType.CROSS_TENANT_ACCESS_ATTEMPT,
            user_id=auth.user.id,
            organization_id=active_org_id,
            route="/api/vault/documents/archive",
            details={
                "requested_tenant_id": int(tenant_id),
                "active_organization_id": int(active_org_id),
            },
        )
        try:
            db.commit()
        except Exception:
            db.rollback()
        return JSONResponse(
            status_code=403,
            content={
                "detail": {
                    "code": "cross_tenant_denied",
                    "message": "Le tenant_id ne correspond pas à l’organisation active",
                }
            },
        )

    from app.billing.billing_guards import check_and_consume_quota, require_feature
    from app.billing.billing_types import FeatureCodes, QuotaCodes

    require_feature(db, active_org_id, FeatureCodes.DOCUMENTS_UPLOAD, user=auth.user)
    check_and_consume_quota(db, active_org_id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, 1)

    try:
        try:
            doc_type = VaultDocumentType(document_type)
        except ValueError as exc:
            raise VaultInvalidFileError("Type de document invalide") from exc

        meta = VaultArchiveFormMeta(
            tenant_id=active_org_id,
            document_type=doc_type,
            document_number=document_number,
            invoice_date=_parse_optional_date(invoice_date),
            due_date=_parse_optional_date(due_date),
            amount_ht=_parse_optional_decimal(amount_ht),
            amount_vat=_parse_optional_decimal(amount_vat),
            amount_ttc=_parse_optional_decimal(amount_ttc),
            currency=currency or "EUR",
            customer_id=_parse_optional_int(customer_id),
            supplier_id=_parse_optional_int(supplier_id),
        )
        content = await file.read()
        result = vault_service.archive_document(
            db,
            user_id=auth.user.id,
            meta=meta,
            filename=file.filename,
            content_type=file.content_type,
            content=content,
        )
        return result
    except VaultAccessDeniedError:
        return JSONResponse(status_code=403, content={"detail": ACCESS_DENIED_MESSAGE})
    except VaultDuplicateDocumentError as exc:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "Ce document est déjà présent dans ELFIS Vault.",
                "existing_document_id": exc.existing_document_id,
            },
        )
    except VaultFileTooLargeError as exc:
        return JSONResponse(status_code=413, content={"detail": str(exc)})
    except VaultInvalidFileError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": exc.errors()})
    except VaultStorageError:
        return JSONResponse(
            status_code=503,
            content={"detail": "Stockage temporairement indisponible"},
        )
    except VaultDatabaseError:
        return JSONResponse(
            status_code=500,
            content={"detail": "Erreur interne lors de l'archivage"},
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except Exception:
        logger.exception("vault_archive_unhandled")
        return JSONResponse(status_code=500, content={"detail": "Erreur interne"})


@router.get("/documents", response_model=VaultDocumentListResponse)
def list_vault_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    document_type: VaultDocumentType | None = Query(default=None),
    archive_status: VaultArchiveStatus | None = Query(default=None),
    search: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    sort_by: VaultSortBy = Query(default=VaultSortBy.created_at),
    sort_order: VaultSortOrder = Query(default=VaultSortOrder.desc),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        return JSONResponse(status_code=401, content={"detail": "Authentification requise"})
    try:
        organization_id = auth.require_organization_id()
        return vault_service.list_documents(
            db,
            user_id=auth.user.id,
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            document_type=document_type,
            archive_status=archive_status,
            search=search,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except VaultAccessDeniedError:
        return JSONResponse(status_code=403, content={"detail": ORG_ACCESS_DENIED_MESSAGE})
    except VaultValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except Exception:
        logger.exception("vault_list_unhandled")
        return JSONResponse(status_code=500, content={"detail": "Erreur interne"})


@router.get("/documents/{document_id}", response_model=VaultDocumentDetail)
def get_vault_document(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        return JSONResponse(status_code=401, content={"detail": "Authentification requise"})
    try:
        organization_id = auth.require_organization_id()
        return vault_service.get_document_details(
            db,
            user_id=auth.user.id,
            organization_id=organization_id,
            document_id=document_id,
        )
    except VaultAccessDeniedError:
        return JSONResponse(status_code=403, content={"detail": ORG_ACCESS_DENIED_MESSAGE})
    except VaultNotFoundError:
        return JSONResponse(status_code=404, content={"detail": DOCUMENT_NOT_FOUND_MESSAGE})
    except Exception:
        logger.exception("vault_detail_unhandled")
        return JSONResponse(status_code=500, content={"detail": "Erreur interne"})


@router.post(
    "/documents/{document_id}/download-url",
    response_model=VaultDownloadUrlResponse,
)
def create_vault_download_url(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if auth.user is None:
        return JSONResponse(status_code=401, content={"detail": "Authentification requise"})
    try:
        organization_id = auth.require_organization_id()
        return vault_service.create_download_url(
            db,
            user_id=auth.user.id,
            organization_id=organization_id,
            document_id=document_id,
        )
    except VaultAccessDeniedError:
        return JSONResponse(status_code=403, content={"detail": ORG_ACCESS_DENIED_MESSAGE})
    except VaultNotFoundError:
        return JSONResponse(status_code=404, content={"detail": DOCUMENT_NOT_FOUND_MESSAGE})
    except VaultStorageError:
        return JSONResponse(
            status_code=503,
            content={"detail": "Stockage temporairement indisponible"},
        )
    except Exception:
        logger.exception("vault_download_url_unhandled")
        return JSONResponse(status_code=500, content={"detail": "Erreur interne"})
