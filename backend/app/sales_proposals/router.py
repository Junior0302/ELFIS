"""Commercial Proposal Engine V1 — REST API /api/sales/proposals/*.

No automatic invoice creation, no automatic email sending. All amounts are
computed server-side (Decimal). See service.py for the workflow state machine.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.sales_crm.permissions import SALES_ADMIN, SALES_MANAGE, SALES_READ, SALES_WRITE
from app.sales_crm.schemas import SalesListResponse

from app.sales_proposals.models import CommercialProposalVersion
from app.sales_proposals.permissions import (
    PROPOSALS_ACCEPT,
    PROPOSALS_APPROVE,
    PROPOSALS_CONVERT,
    PROPOSALS_DELETE,
    PROPOSALS_READ,
    PROPOSALS_SEND,
    PROPOSALS_WRITE,
)
from app.sales_proposals.schemas import (
    AcceptIn,
    ConversionCustomerIn,
    ConversionPreviewOut,
    ConversionStateOut,
    ConvertToInvoiceIn,
    ConvertToInvoiceOut,
    DiffOut,
    InvoiceConversionPreviewOut,
    LineCreate,
    LineOut,
    LineUpdate,
    ProposalCreate,
    ProposalOut,
    ProposalUpdate,
    RejectIn,
    VersionOut,
    WorkspaceOut,
)
from app.sales_proposals.service import ProposalService

router = APIRouter(
    prefix="/sales/proposals",
    tags=["sales-proposals"],
    dependencies=[Depends(require_active_subscription)],
)


def _has(auth: AuthContext, *codes: str) -> bool:
    """True si l'utilisateur a le joker '*' ou l'un des codes fournis."""
    perms = auth.permissions or []
    if "*" in perms:
        return True
    return any(code in perms for code in codes)


def _require(auth: AuthContext, *codes: str) -> None:
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")
    if not _has(auth, *codes):
        raise HTTPException(
            403,
            detail={
                "code": "permission_denied",
                "message": "Permission refusée",
                "permission": codes[0] if codes else None,
            },
        )


def _require_read(auth: AuthContext) -> None:
    _require(auth, PROPOSALS_READ, SALES_READ)


def _require_write(auth: AuthContext) -> None:
    _require(auth, PROPOSALS_WRITE, SALES_WRITE)


def _require_approve(auth: AuthContext) -> None:
    _require(auth, PROPOSALS_APPROVE, SALES_MANAGE, SALES_ADMIN)


def _require_send(auth: AuthContext) -> None:
    _require(auth, PROPOSALS_SEND, SALES_WRITE)


def _require_accept(auth: AuthContext) -> None:
    _require(auth, PROPOSALS_ACCEPT, SALES_WRITE)


def _require_convert(auth: AuthContext) -> None:
    _require(auth, PROPOSALS_CONVERT, SALES_MANAGE)


def _require_delete(auth: AuthContext) -> None:
    _require(auth, PROPOSALS_DELETE, SALES_ADMIN)


def _uid(auth: AuthContext) -> int | None:
    return auth.user.id if auth.user else None


def _version_out(version, lines) -> VersionOut:
    return VersionOut.model_validate(
        {
            "id": version.id,
            "proposal_id": version.proposal_id,
            "version_number": version.version_number,
            "status": version.status,
            "title": version.title,
            "introduction": version.introduction,
            "scope": version.scope,
            "terms": version.terms,
            "payment_terms": version.payment_terms,
            "notes": version.notes,
            "subtotal": version.subtotal,
            "discount_total": version.discount_total,
            "tax_total": version.tax_total,
            "total": version.total,
            "currency": version.currency,
            "valid_until": version.valid_until,
            "readiness_score": version.readiness_score,
            "readiness_level": version.readiness_level,
            "readiness_explanation": version.readiness_explanation or {},
            "pdf_vault_document_id": version.pdf_vault_document_id,
            "checksum": version.checksum,
            "created_at": version.created_at,
            "updated_at": version.updated_at,
            "sent_at": version.sent_at,
            "viewed_at": version.viewed_at,
            "accepted_at": version.accepted_at,
            "rejected_at": version.rejected_at,
            "locked_at": version.locked_at,
            "lines": lines,
        }
    )


# ----- Proposals -----


@router.post("", response_model=ProposalOut, status_code=201)
def create_proposal(
    body: ProposalCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_write(auth)
    org_id = auth.require_organization_id()
    proposal = ProposalService(db).create_proposal(organization_id=org_id, user_id=_uid(auth), data=body)
    db.commit()
    db.refresh(proposal)
    return ProposalOut.model_validate(proposal)


@router.get("", response_model=SalesListResponse[ProposalOut])
def list_proposals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    status: str | None = None,
    sort: str = "-updated_at",
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_read(auth)
    org_id = auth.require_organization_id()
    items, pagination = ProposalService(db).list_proposals(
        organization_id=org_id, page=page, page_size=page_size, q=q, status=status, sort=sort
    )
    return SalesListResponse(items=[ProposalOut.model_validate(i) for i in items], pagination=pagination)


@router.get("/{proposal_id}", response_model=ProposalOut)
def get_proposal(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_read(auth)
    org_id = auth.require_organization_id()
    proposal = ProposalService(db).get_proposal(organization_id=org_id, proposal_id=proposal_id)
    return ProposalOut.model_validate(proposal)


@router.patch("/{proposal_id}", response_model=ProposalOut)
def update_proposal(
    proposal_id: int,
    body: ProposalUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_write(auth)
    org_id = auth.require_organization_id()
    proposal = ProposalService(db).update_proposal_meta(
        organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id, data=body
    )
    db.commit()
    db.refresh(proposal)
    return ProposalOut.model_validate(proposal)


@router.delete("/{proposal_id}", status_code=204)
def delete_proposal(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_delete(auth)
    org_id = auth.require_organization_id()
    ProposalService(db).soft_delete_proposal(organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id)
    db.commit()
    return Response(status_code=204)


@router.get("/{proposal_id}/workspace", response_model=WorkspaceOut)
def get_workspace(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_read(auth)
    org_id = auth.require_organization_id()
    payload = ProposalService(db).build_workspace(organization_id=org_id, proposal_id=proposal_id)
    db.commit()
    return WorkspaceOut.model_validate(payload)


# ----- Versions -----


@router.post("/{proposal_id}/versions", response_model=VersionOut, status_code=201)
def create_version(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_write(auth)
    org_id = auth.require_organization_id()
    service = ProposalService(db)
    version = service.create_new_version_from_current(
        organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id
    )
    db.commit()
    db.refresh(version)
    lines = service.lines_for_version(version.id)
    return _version_out(version, lines)


@router.get("/{proposal_id}/versions", response_model=list[VersionOut])
def list_versions(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_read(auth)
    org_id = auth.require_organization_id()
    service = ProposalService(db)
    proposal = service.get_proposal(organization_id=org_id, proposal_id=proposal_id)
    rows = (
        db.query(CommercialProposalVersion)
        .filter(
            CommercialProposalVersion.proposal_id == proposal.id,
            CommercialProposalVersion.deleted_at.is_(None),
        )
        .order_by(CommercialProposalVersion.version_number.desc())
        .all()
    )
    return [_version_out(v, service.lines_for_version(v.id)) for v in rows]


@router.get("/{proposal_id}/versions/compare", response_model=DiffOut)
def compare_versions(
    proposal_id: int,
    from_version_id: int = Query(...),
    to_version_id: int = Query(...),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_read(auth)
    org_id = auth.require_organization_id()
    diff = ProposalService(db).compare_versions(
        organization_id=org_id,
        proposal_id=proposal_id,
        from_version_id=from_version_id,
        to_version_id=to_version_id,
    )
    return DiffOut.model_validate(diff)


@router.get("/{proposal_id}/versions/{version_id}", response_model=VersionOut)
def get_version(
    proposal_id: int,
    version_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_read(auth)
    org_id = auth.require_organization_id()
    service = ProposalService(db)
    service.get_proposal(organization_id=org_id, proposal_id=proposal_id)
    version = service.get_version(organization_id=org_id, proposal_id=proposal_id, version_id=version_id)
    lines = service.lines_for_version(version.id)
    return _version_out(version, lines)


# ----- Lines (on the current version) -----


@router.post("/{proposal_id}/lines", response_model=LineOut, status_code=201)
def add_line(
    proposal_id: int,
    body: LineCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_write(auth)
    org_id = auth.require_organization_id()
    line = ProposalService(db).add_line(
        organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id, data=body
    )
    db.commit()
    db.refresh(line)
    return LineOut.model_validate(line)


@router.patch("/{proposal_id}/lines/{line_id}", response_model=LineOut)
def update_line(
    proposal_id: int,
    line_id: int,
    body: LineUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_write(auth)
    org_id = auth.require_organization_id()
    line = ProposalService(db).update_line(
        organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id, line_id=line_id, data=body
    )
    db.commit()
    db.refresh(line)
    return LineOut.model_validate(line)


@router.delete("/{proposal_id}/lines/{line_id}", status_code=204)
def delete_line(
    proposal_id: int,
    line_id: int,
    expected_updated_at: datetime | None = Query(default=None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_write(auth)
    org_id = auth.require_organization_id()
    ProposalService(db).delete_line(
        organization_id=org_id,
        user_id=_uid(auth),
        proposal_id=proposal_id,
        line_id=line_id,
        expected_updated_at=expected_updated_at,
    )
    db.commit()
    return Response(status_code=204)


# ----- Workflow actions -----


@router.post("/{proposal_id}/prepare", response_model=ProposalOut)
def action_prepare(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_write(auth)
    org_id = auth.require_organization_id()
    proposal = ProposalService(db).prepare(organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id)
    db.commit()
    db.refresh(proposal)
    return ProposalOut.model_validate(proposal)


@router.post("/{proposal_id}/request-review", response_model=ProposalOut)
def action_request_review(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_write(auth)
    org_id = auth.require_organization_id()
    proposal = ProposalService(db).request_review(
        organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id
    )
    db.commit()
    db.refresh(proposal)
    return ProposalOut.model_validate(proposal)


@router.post("/{proposal_id}/approve", response_model=ProposalOut)
def action_approve(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_approve(auth)
    org_id = auth.require_organization_id()
    proposal = ProposalService(db).approve(organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id)
    db.commit()
    db.refresh(proposal)
    return ProposalOut.model_validate(proposal)


@router.post("/{proposal_id}/mark-sent", response_model=ProposalOut)
def action_mark_sent(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_send(auth)
    org_id = auth.require_organization_id()
    proposal = ProposalService(db).mark_sent(organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id)
    db.commit()
    db.refresh(proposal)
    return ProposalOut.model_validate(proposal)


@router.post("/{proposal_id}/mark-viewed", response_model=ProposalOut)
def action_mark_viewed(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_write(auth)
    org_id = auth.require_organization_id()
    proposal = ProposalService(db).mark_viewed(organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id)
    db.commit()
    db.refresh(proposal)
    return ProposalOut.model_validate(proposal)


@router.post("/{proposal_id}/start-negotiation", response_model=ProposalOut)
def action_start_negotiation(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_write(auth)
    org_id = auth.require_organization_id()
    proposal = ProposalService(db).start_negotiation(
        organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id
    )
    db.commit()
    db.refresh(proposal)
    return ProposalOut.model_validate(proposal)


@router.post("/{proposal_id}/accept", response_model=ProposalOut)
def action_accept(
    proposal_id: int,
    body: AcceptIn = AcceptIn(),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_accept(auth)
    org_id = auth.require_organization_id()
    proposal = ProposalService(db).accept(
        organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id, data=body
    )
    db.commit()
    db.refresh(proposal)
    return ProposalOut.model_validate(proposal)


@router.post("/{proposal_id}/reject", response_model=ProposalOut)
def action_reject(
    proposal_id: int,
    body: RejectIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_accept(auth)
    org_id = auth.require_organization_id()
    proposal = ProposalService(db).reject(
        organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id, data=body
    )
    db.commit()
    db.refresh(proposal)
    return ProposalOut.model_validate(proposal)


@router.post("/{proposal_id}/expire", response_model=ProposalOut)
def action_expire(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_write(auth)
    org_id = auth.require_organization_id()
    proposal = ProposalService(db).expire(organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id)
    db.commit()
    db.refresh(proposal)
    return ProposalOut.model_validate(proposal)


@router.post("/{proposal_id}/cancel", response_model=ProposalOut)
def action_cancel(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_write(auth)
    org_id = auth.require_organization_id()
    proposal = ProposalService(db).cancel(organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id)
    db.commit()
    db.refresh(proposal)
    return ProposalOut.model_validate(proposal)


# ----- PDF & conversion -----


@router.post("/{proposal_id}/generate-pdf", response_model=VersionOut)
def generate_pdf(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_send(auth)
    org_id = auth.require_organization_id()
    service = ProposalService(db)
    version = service.generate_pdf(organization_id=org_id, user_id=_uid(auth), proposal_id=proposal_id)
    db.commit()
    db.refresh(version)
    lines = service.lines_for_version(version.id)
    return _version_out(version, lines)


@router.post("/{proposal_id}/prepare-conversion", response_model=ConversionPreviewOut)
def prepare_conversion(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_convert(auth)
    org_id = auth.require_organization_id()
    payload = ProposalService(db).prepare_conversion_bridge(organization_id=org_id, proposal_id=proposal_id)
    db.commit()
    return ConversionPreviewOut.model_validate(payload)


@router.get("/{proposal_id}/conversion-state", response_model=ConversionStateOut)
def conversion_state(
    proposal_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_convert(auth)
    org_id = auth.require_organization_id()
    from app.sales_proposals.invoice_bridge import ProposalInvoiceConversionService

    payload = ProposalInvoiceConversionService(db).build_conversion_state(
        organization_id=org_id, proposal_id=proposal_id
    )
    return ConversionStateOut.model_validate(payload)


@router.post("/{proposal_id}/conversion-preview", response_model=InvoiceConversionPreviewOut)
def conversion_preview(
    proposal_id: int,
    customer_id: int | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_convert(auth)
    org_id = auth.require_organization_id()
    from app.sales_proposals.invoice_bridge import ProposalInvoiceConversionService

    payload = ProposalInvoiceConversionService(db).build_invoice_preview(
        organization_id=org_id, proposal_id=proposal_id, customer_id=customer_id
    )
    return InvoiceConversionPreviewOut.model_validate(payload)


@router.post("/{proposal_id}/conversion/customer")
def conversion_customer(
    proposal_id: int,
    body: ConversionCustomerIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_convert(auth)
    org_id = auth.require_organization_id()
    from app.sales_proposals.invoice_bridge import ProposalInvoiceConversionService

    if body.customer_resolution_mode == "create_new_customer":
        if not _has(auth, "invoice.create", "*"):
            raise HTTPException(
                403,
                detail={
                    "code": "permission_denied",
                    "message": "Permission facturation (invoice.create) requise pour créer un client",
                },
            )
    payload = body.customer_payload or {}
    if body.force_create:
        payload = {**payload, "force_create": True}
    result = ProposalInvoiceConversionService(db).link_or_create_customer(
        organization_id=org_id,
        proposal_id=proposal_id,
        user_id=_uid(auth),
        mode=body.customer_resolution_mode,
        customer_id=body.customer_id,
        customer_payload=payload,
        confirm_possible_match=body.confirm_possible_match,
    )
    db.commit()
    return result


@router.post("/{proposal_id}/convert-to-invoice", response_model=ConvertToInvoiceOut)
def convert_to_invoice(
    proposal_id: int,
    body: ConvertToInvoiceIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_convert(auth)
    if not _has(auth, "invoice.create", "*"):
        raise HTTPException(
            403,
            detail={
                "code": "permission_denied",
                "message": "Permission facturation (invoice.create) requise pour convertir",
            },
        )
    org_id = auth.require_organization_id()
    from app.sales_proposals.invoice_bridge import ProposalInvoiceConversionService

    try:
        result = ProposalInvoiceConversionService(db).convert_to_invoice(
            organization_id=org_id,
            proposal_id=proposal_id,
            user_id=_uid(auth),
            customer_resolution_mode=body.customer_resolution_mode,
            customer_id=body.customer_id,
            customer_payload=body.customer_payload,
            accepted_version_id=body.accepted_version_id,
            expected_proposal_updated_at=body.expected_proposal_updated_at,
            idempotency_key=body.idempotency_key,
            confirm_possible_match=body.confirm_possible_match,
        )
        db.commit()
        return ConvertToInvoiceOut.model_validate(result)
    except HTTPException:
        db.rollback()
        raise
