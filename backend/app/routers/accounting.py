"""Routes Accounting Pipeline — utilisateur + plateforme."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.accounting.accounting_exceptions import (
    AccountingDisabledError,
    AccountingNotFoundError,
    AccountingPermissionError,
    AccountingStateError,
    AccountingValidationError,
)
from app.accounting.accounting_repository import AccountingRepository
from app.accounting.accounting_schemas import (
    AccountingProposalUpdate,
    AccountingRejectionRequest,
    AccountingValidationRequest,
    BuildProposalAccepted,
)
from app.accounting.accounting_security import check_accounting_permission
from app.accounting.accounting_service import AccountingService
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription, require_platform_admin
from app.jobs import bootstrap_job_handlers
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames
from app.models_saas import User
from app.models_vault import VaultDocument
import uuid

router = APIRouter(prefix="/accounting", tags=["accounting"])
platform_router = APIRouter(
    prefix="/platform/accounting",
    tags=["platform-accounting"],
    dependencies=[Depends(require_platform_admin)],
)


def _perm(auth: AuthContext, action: str) -> None:
    try:
        check_accounting_permission(auth.permissions, action)
    except AccountingPermissionError as exc:
        raise HTTPException(403, detail=exc.message) from None


@router.get("/proposals", dependencies=[Depends(require_active_subscription)])
def list_proposals(
    status: str | None = None,
    document_type: str | None = None,
    requires_review: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    _perm(auth, "view")
    org_id = auth.require_organization_id()
    items, total = AccountingService(db).list_proposals(
        organization_id=org_id,
        status=status,
        document_type=document_type,
        requires_review=requires_review,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "proposals": [i.model_dump() for i in items],
    }


@router.get("/proposals/{proposal_id}", dependencies=[Depends(require_active_subscription)])
def get_proposal(
    proposal_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    _perm(auth, "view")
    org_id = auth.require_organization_id()
    try:
        detail = AccountingService(db).get_proposal(
            organization_id=org_id, proposal_id=proposal_id
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(404, detail=exc.message) from None
    return detail.model_dump()


@router.put("/proposals/{proposal_id}", dependencies=[Depends(require_active_subscription)])
def update_proposal(
    proposal_id: str,
    body: AccountingProposalUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    _perm(auth, "edit")
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    try:
        detail = AccountingService(db).update_proposal(
            organization_id=org_id,
            proposal_id=proposal_id,
            user_id=auth.user.id,
            data=body,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(404, detail=exc.message) from None
    except (AccountingStateError, AccountingValidationError) as exc:
        raise HTTPException(400, detail=exc.message) from None
    return detail.model_dump()


@router.post(
    "/proposals/{proposal_id}/validate",
    dependencies=[Depends(require_active_subscription)],
)
def validate_proposal(
    proposal_id: str,
    body: AccountingValidationRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    _perm(auth, "validate")
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    try:
        detail = AccountingService(db).validate_proposal(
            organization_id=org_id,
            proposal_id=proposal_id,
            user_id=auth.user.id,
            body=body,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(404, detail=exc.message) from None
    except AccountingPermissionError as exc:
        raise HTTPException(403, detail={"code": "permission_denied", "message": exc.message}) from None
    except (AccountingStateError, AccountingValidationError) as exc:
        raise HTTPException(400, detail=exc.message) from None
    return detail.model_dump()


@router.post(
    "/proposals/{proposal_id}/reject",
    dependencies=[Depends(require_active_subscription)],
)
def reject_proposal(
    proposal_id: str,
    body: AccountingRejectionRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    _perm(auth, "reject")
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    try:
        detail = AccountingService(db).reject_proposal(
            organization_id=org_id,
            proposal_id=proposal_id,
            user_id=auth.user.id,
            body=body,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(404, detail=exc.message) from None
    except AccountingPermissionError as exc:
        raise HTTPException(403, detail={"code": "permission_denied", "message": exc.message}) from None
    except AccountingStateError as exc:
        raise HTTPException(400, detail=exc.message) from None
    return detail.model_dump()


@router.post(
    "/proposals/{proposal_id}/reopen",
    dependencies=[Depends(require_active_subscription)],
)
def reopen_proposal(
    proposal_id: str,
    comment: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    _perm(auth, "reopen")
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    try:
        detail = AccountingService(db).reopen_proposal(
            organization_id=org_id,
            proposal_id=proposal_id,
            user_id=auth.user.id,
            comment=comment,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(404, detail=exc.message) from None
    except AccountingStateError as exc:
        raise HTTPException(400, detail=exc.message) from None
    return detail.model_dump()


@router.post(
    "/documents/{vault_document_id}/build-proposal",
    status_code=202,
    dependencies=[Depends(require_active_subscription)],
)
def build_proposal(
    vault_document_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    _perm(auth, "edit")
    bootstrap_job_handlers()
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    doc = db.query(VaultDocument).filter(VaultDocument.id == vault_document_id).first()
    if not doc or doc.organization_id != org_id:
        raise HTTPException(404, detail="Document introuvable")
    version = int(doc.version or 1)
    existing = AccountingRepository(db).find_proposal_for_document(
        organization_id=org_id,
        vault_document_id=vault_document_id,
        document_version=version,
    )
    if existing and existing.status in (
        "ready_for_validation",
        "requires_review",
        "validated",
        "processing",
    ):
        return BuildProposalAccepted(
            proposal_id=existing.proposal_id,
            job_id=existing.job_id,
            status=existing.status,
            reused_existing=True,
        ).model_dump()

    idem = f"accounting-proposal:{org_id}:{vault_document_id}:{version}"
    try:
        job = JobService(db).enqueue(
            JobRequest(
                job_name=JobNames.ACCOUNTING_BUILD_PROPOSAL,
                organization_id=org_id,
                user_id=auth.user.id,
                payload={
                    "vault_document_id": vault_document_id,
                    "document_version": version,
                },
                idempotency_key=idem,
                correlation_id=str(uuid.uuid4()),
            )
        )
    except AccountingDisabledError as exc:
        raise HTTPException(503, detail=exc.message) from None
    return BuildProposalAccepted(
        proposal_id=existing.proposal_id if existing else None,
        job_id=job.job_id,
        status="pending",
        reused_existing=False,
    ).model_dump()


@platform_router.get("/proposals")
def platform_list_proposals(
    organization_id: int | None = None,
    status: str | None = None,
    document_type: str | None = None,
    requires_review: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    _ = admin
    rows, total = AccountingRepository(db).list_proposals(
        organization_id=organization_id,
        status=status,
        document_type=document_type,
        requires_review=requires_review,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "proposals": [
            {
                "proposal_id": r.proposal_id,
                "organization_id": r.organization_id,
                "vault_document_id": r.vault_document_id,
                "document_type": r.document_type,
                "status": r.status,
                "requires_review": r.requires_review,
                "confidence": float(r.confidence) if r.confidence is not None else None,
                "amount_ttc": float(r.amount_ttc) if r.amount_ttc is not None else None,
                "created_at": r.created_at,
                "validated_by_user_id": r.validated_by_user_id,
            }
            for r in rows
        ],
    }


@platform_router.get("/proposals/{proposal_id}")
def platform_get_proposal(
    proposal_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    _ = admin
    row = AccountingRepository(db).find_proposal(proposal_id)
    if not row:
        raise HTTPException(404, detail="Proposition introuvable")
    detail = AccountingService(db)._to_detail(row)
    data = detail.model_dump()
    data["organization_id"] = row.organization_id
    return data


@platform_router.get("/entries")
def platform_list_entries(
    organization_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    _ = admin
    rows, total = AccountingRepository(db).list_entries(
        organization_id=organization_id, status=status, page=page, page_size=page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "entries": [
            {
                "entry_id": r.entry_id,
                "organization_id": r.organization_id,
                "proposal_id": r.proposal_id,
                "journal_code": r.journal_code,
                "total_debit": float(r.total_debit or 0),
                "total_credit": float(r.total_credit or 0),
                "balanced": r.balanced,
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


@platform_router.get("/reviews")
def platform_list_reviews(
    organization_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    _ = admin
    rows, total = AccountingRepository(db).list_all_reviews(
        organization_id=organization_id, page=page, page_size=page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "reviews": [
            {
                "review_id": r.review_id,
                "organization_id": r.organization_id,
                "proposal_id": r.proposal_id,
                "user_id": r.user_id,
                "action": r.action,
                "comment": r.comment,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }
