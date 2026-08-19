"""Commercial Proposal Engine V1 — service layer.

SalesPilot owns the proposal lifecycle end-to-end (draft → sent →
accepted/rejected/expired). Business rules enforced here:

- No automatic invoice creation, no automatic email sending (see conversion.py).
- Amounts are always Decimal, computed server-side (app.sales_proposals.amounts).
- A version becomes immutable ("locked") once it reaches a post-send status
  (LOCKED_VERSION_STATUSES) — editing then requires creating a new version.
- Every meaningful transition is recorded on the append-only timeline
  (CommercialProposalEvent) and published on the event bus (best-effort).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from math import ceil
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.events.event_types import EventNames
from app.models_saas import Customer, Organization
from app.schemas_vault import VaultDocumentType
from app.sales_crm.models import SalesCompany, SalesOpportunity, SalesOpportunityProduct, SalesPerson
from app.sales_crm.schemas import SalesPagination
from app.services.vault.vault_service import archive_or_reuse_pdf

from app.sales_proposals.amounts import compute_line_amounts, money, qty, sum_totals
from app.sales_proposals.conversion import prepare_conversion
from app.sales_proposals.diff import compare_versions as diff_compare_versions
from app.sales_proposals.enums import (
    ALLOWED_TRANSITIONS,
    AmountMode,
    DiscountType,
    LOCKED_VERSION_STATUSES,
    ProposalStatus,
    VersionStatus,
)
from app.sales_proposals.events import publish_proposal_event
from app.sales_proposals.models import (
    CommercialProposal,
    CommercialProposalEvent,
    CommercialProposalLine,
    CommercialProposalVersion,
)
from app.sales_proposals.numbering import next_proposal_number
from app.sales_proposals.pdf_service import proposal_version_to_pdf
from app.sales_proposals.readiness import compute_readiness, lines_are_valid
from app.sales_proposals.schemas import (
    AcceptIn,
    LineCreate,
    LineUpdate,
    ProposalCreate,
    ProposalUpdate,
    RejectIn,
)

EVENT_PROPOSAL_PREPARING = "sales.proposal.preparing.v1"
EVENT_PROPOSAL_CANCELLED = "sales.proposal.cancelled.v1"


def _now() -> datetime:
    return datetime.utcnow()


class ProposalService:
    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------------------------------- #
    # Internal lookups
    # ----------------------------------------------------------------- #

    def _now(self) -> datetime:
        return _now()

    def _locked_statuses(self) -> set[str]:
        return {s.value for s in LOCKED_VERSION_STATUSES}

    def _get_proposal(self, organization_id: int, proposal_id: int) -> CommercialProposal:
        row = (
            self.db.query(CommercialProposal)
            .filter(
                CommercialProposal.id == proposal_id,
                CommercialProposal.organization_id == organization_id,
                CommercialProposal.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise HTTPException(
                404, detail={"code": "not_found", "message": "Proposition commerciale introuvable"}
            )
        return row

    def _get_version(
        self, organization_id: int, proposal_id: int, version_id: int
    ) -> CommercialProposalVersion:
        row = (
            self.db.query(CommercialProposalVersion)
            .filter(
                CommercialProposalVersion.id == version_id,
                CommercialProposalVersion.proposal_id == proposal_id,
                CommercialProposalVersion.organization_id == organization_id,
                CommercialProposalVersion.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise HTTPException(
                404, detail={"code": "not_found", "message": "Version de proposition introuvable"}
            )
        return row

    def _get_current_version(self, proposal: CommercialProposal) -> CommercialProposalVersion:
        if not proposal.current_version_id:
            raise HTTPException(
                409, detail={"code": "no_current_version", "message": "Aucune version courante"}
            )
        version = self.db.get(CommercialProposalVersion, proposal.current_version_id)
        if not version or version.deleted_at is not None:
            raise HTTPException(
                409, detail={"code": "no_current_version", "message": "Version courante introuvable"}
            )
        return version

    def _get_line(self, version_id: int, line_id: int) -> CommercialProposalLine:
        row = (
            self.db.query(CommercialProposalLine)
            .filter(
                CommercialProposalLine.id == line_id,
                CommercialProposalLine.proposal_version_id == version_id,
                CommercialProposalLine.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise HTTPException(404, detail={"code": "not_found", "message": "Ligne introuvable"})
        return row

    def _lines_for_version(self, version_id: int) -> list[CommercialProposalLine]:
        return (
            self.db.query(CommercialProposalLine)
            .filter(
                CommercialProposalLine.proposal_version_id == version_id,
                CommercialProposalLine.deleted_at.is_(None),
            )
            .order_by(CommercialProposalLine.position.asc(), CommercialProposalLine.id.asc())
            .all()
        )

    def _require_editable(self, version: CommercialProposalVersion) -> None:
        if version.status in self._locked_statuses():
            raise HTTPException(
                409,
                detail={
                    "code": "version_locked",
                    "message": "Version verrouillée : créez une nouvelle version pour la modifier",
                },
            )

    def _check_version_concurrency(
        self, version: CommercialProposalVersion, expected_updated_at: datetime | None
    ) -> None:
        if expected_updated_at is not None and version.updated_at != expected_updated_at:
            raise HTTPException(
                409,
                detail={
                    "code": "conflict",
                    "message": "La version a été modifiée entre-temps, veuillez rafraîchir avant de réessayer",
                },
            )

    # ----------------------------------------------------------------- #
    # Proposal CRUD
    # ----------------------------------------------------------------- #

    def create_proposal(
        self, *, organization_id: int, user_id: int | None, data: ProposalCreate
    ) -> CommercialProposal:
        opportunity: SalesOpportunity | None = None
        if data.opportunity_id:
            opportunity = (
                self.db.query(SalesOpportunity)
                .filter(
                    SalesOpportunity.id == data.opportunity_id,
                    SalesOpportunity.organization_id == organization_id,
                    SalesOpportunity.deleted_at.is_(None),
                )
                .first()
            )
            if not opportunity:
                raise HTTPException(404, detail={"code": "not_found", "message": "Opportunité introuvable"})

        if data.sales_company_id:
            company_exists = (
                self.db.query(SalesCompany.id)
                .filter(
                    SalesCompany.id == data.sales_company_id,
                    SalesCompany.organization_id == organization_id,
                    SalesCompany.deleted_at.is_(None),
                )
                .first()
            )
            if not company_exists:
                raise HTTPException(404, detail={"code": "not_found", "message": "Entreprise introuvable"})

        if data.person_id:
            person_exists = (
                self.db.query(SalesPerson.id)
                .filter(
                    SalesPerson.id == data.person_id,
                    SalesPerson.organization_id == organization_id,
                    SalesPerson.deleted_at.is_(None),
                )
                .first()
            )
            if not person_exists:
                raise HTTPException(404, detail={"code": "not_found", "message": "Contact introuvable"})

        number = next_proposal_number(self.db, organization_id=organization_id)
        now = self._now()
        company_id = data.sales_company_id
        person_id = data.person_id
        if opportunity is not None:
            if company_id is None:
                company_id = opportunity.company_id
            if person_id is None:
                person_id = opportunity.person_id
        proposal = CommercialProposal(
            organization_id=organization_id,
            opportunity_id=data.opportunity_id,
            sales_company_id=company_id,
            person_id=person_id,
            proposal_number=number,
            proposal_type=data.proposal_type.value,
            status=ProposalStatus.draft.value,
            owner_user_id=user_id,
            currency=data.currency,
            valid_until=data.valid_until,
            created_by=user_id,
            updated_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(proposal)
        self.db.flush()

        version = CommercialProposalVersion(
            organization_id=organization_id,
            proposal_id=proposal.id,
            version_number=1,
            status=VersionStatus.draft.value,
            title=data.title or "Proposition commerciale",
            currency=data.currency,
            valid_until=data.valid_until,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(version)
        self.db.flush()
        proposal.current_version_id = version.id

        if data.seed_from_opportunity_products and opportunity is not None:
            self._seed_lines_from_opportunity(version, opportunity)

        self._recompute_version_totals(version)
        self._refresh_readiness(proposal, version)

        self._record_event(
            proposal,
            version,
            event_type=EventNames.SALES_PROPOSAL_CREATED,
            title=f"Proposition {proposal.proposal_number} créée",
            payload={
                "proposal_number": proposal.proposal_number,
                "proposal_type": proposal.proposal_type,
                "opportunity_id": proposal.opportunity_id,
                "amount_source": data.amount_source,
            },
            actor_user_id=user_id,
        )
        return proposal

    def _seed_lines_from_opportunity(
        self, version: CommercialProposalVersion, opportunity: SalesOpportunity
    ) -> None:
        products = (
            self.db.query(SalesOpportunityProduct)
            .filter(
                SalesOpportunityProduct.opportunity_id == opportunity.id,
                SalesOpportunityProduct.deleted_at.is_(None),
            )
            .order_by(SalesOpportunityProduct.position.asc(), SalesOpportunityProduct.id.asc())
            .all()
        )
        default_tax_rate = Decimal("20")
        for idx, product in enumerate(products):
            discount_type = (
                DiscountType.percentage.value
                if (product.discount_percent or Decimal("0")) > 0
                else DiscountType.none.value
            )
            computed = compute_line_amounts(
                quantity=product.quantity,
                unit_price=product.unit_price,
                discount_type=discount_type,
                discount_value=product.discount_percent or Decimal("0"),
                tax_rate=default_tax_rate,
            )
            line = CommercialProposalLine(
                organization_id=version.organization_id,
                proposal_version_id=version.id,
                source_opportunity_product_id=product.id,
                position=product.position if product.position is not None else idx,
                name=product.name,
                description=product.description,
                quantity=qty(product.quantity),
                unit_price=money(product.unit_price),
                discount_type=discount_type,
                discount_value=money(product.discount_percent or Decimal("0")),
                tax_rate=default_tax_rate,
                subtotal=computed["subtotal"],
                discount_amount=computed["discount_amount"],
                tax_amount=computed["tax_amount"],
                total=computed["total"],
            )
            self.db.add(line)
        self.db.flush()

    def list_proposals(
        self,
        *,
        organization_id: int,
        page: int = 1,
        page_size: int = 20,
        q: str | None = None,
        status: str | None = None,
        sort: str = "-updated_at",
    ) -> tuple[list[CommercialProposal], SalesPagination]:
        query = self.db.query(CommercialProposal).filter(
            CommercialProposal.organization_id == organization_id,
            CommercialProposal.deleted_at.is_(None),
        )
        if status:
            query = query.filter(CommercialProposal.status == status)
        if q:
            like = f"%{q.strip()}%"
            query = query.filter(CommercialProposal.proposal_number.ilike(like))

        sort_field = (sort or "-updated_at").lstrip("-")
        column = getattr(CommercialProposal, sort_field, CommercialProposal.updated_at)
        query = query.order_by(column.desc() if (sort or "").startswith("-") else column.asc())

        page = max(1, page)
        page_size = min(100, max(1, page_size))
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        pagination = SalesPagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=max(1, ceil(total / page_size)) if total else 0,
        )
        return items, pagination

    def get_proposal(self, *, organization_id: int, proposal_id: int) -> CommercialProposal:
        return self._get_proposal(organization_id, proposal_id)

    def get_version(
        self, *, organization_id: int, proposal_id: int, version_id: int
    ) -> CommercialProposalVersion:
        return self._get_version(organization_id, proposal_id, version_id)

    def lines_for_version(self, version_id: int) -> list[CommercialProposalLine]:
        return self._lines_for_version(version_id)

    def soft_delete_proposal(self, *, organization_id: int, user_id: int | None, proposal_id: int) -> None:
        proposal = self._get_proposal(organization_id, proposal_id)
        if proposal.status not in (ProposalStatus.draft.value, ProposalStatus.cancelled.value):
            raise HTTPException(
                409,
                detail={
                    "code": "invalid_state",
                    "message": "Seules les propositions en brouillon ou annulées peuvent être supprimées",
                },
            )
        now = self._now()
        proposal.deleted_at = now
        proposal.updated_by = user_id
        proposal.updated_at = now

    def update_proposal_meta(
        self, *, organization_id: int, user_id: int | None, proposal_id: int, data: ProposalUpdate
    ) -> CommercialProposal:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)

        self._check_version_concurrency(version, data.expected_updated_at)

        content_fields = ("title", "introduction", "scope", "terms", "payment_terms", "notes")
        wants_content_update = any(getattr(data, field) is not None for field in content_fields)
        if wants_content_update:
            self._require_editable(version)

        if data.sales_company_id is not None:
            exists = (
                self.db.query(SalesCompany.id)
                .filter(
                    SalesCompany.id == data.sales_company_id,
                    SalesCompany.organization_id == organization_id,
                    SalesCompany.deleted_at.is_(None),
                )
                .first()
            )
            if not exists:
                raise HTTPException(404, detail={"code": "not_found", "message": "Entreprise introuvable"})
            proposal.sales_company_id = data.sales_company_id

        if data.person_id is not None:
            exists = (
                self.db.query(SalesPerson.id)
                .filter(
                    SalesPerson.id == data.person_id,
                    SalesPerson.organization_id == organization_id,
                    SalesPerson.deleted_at.is_(None),
                )
                .first()
            )
            if not exists:
                raise HTTPException(404, detail={"code": "not_found", "message": "Contact introuvable"})
            proposal.person_id = data.person_id

        if data.owner_user_id is not None:
            proposal.owner_user_id = data.owner_user_id
        if data.currency is not None:
            proposal.currency = data.currency
            version.currency = data.currency
        if data.valid_until is not None:
            proposal.valid_until = data.valid_until
            version.valid_until = data.valid_until

        if wants_content_update:
            if data.title is not None:
                version.title = data.title
            if data.introduction is not None:
                version.introduction = data.introduction
            if data.scope is not None:
                version.scope = data.scope
            if data.terms is not None:
                version.terms = data.terms
            if data.payment_terms is not None:
                version.payment_terms = data.payment_terms
            if data.notes is not None:
                version.notes = data.notes
            version.updated_at = self._now()

        proposal.updated_by = user_id
        proposal.updated_at = self._now()
        self._refresh_readiness(proposal, version)
        return proposal

    def create_new_version_from_current(
        self, *, organization_id: int, user_id: int | None, proposal_id: int
    ) -> CommercialProposalVersion:
        proposal = self._get_proposal(organization_id, proposal_id)
        current = self._get_current_version(proposal)
        if proposal.status in (ProposalStatus.converted.value, ProposalStatus.cancelled.value):
            raise HTTPException(
                409,
                detail={
                    "code": "invalid_state",
                    "message": "Impossible de créer une nouvelle version sur une proposition convertie ou annulée",
                },
            )

        version_count = (
            self.db.query(CommercialProposalVersion)
            .filter(CommercialProposalVersion.proposal_id == proposal.id)
            .count()
        )
        now = self._now()
        new_version = CommercialProposalVersion(
            organization_id=organization_id,
            proposal_id=proposal.id,
            version_number=version_count + 1,
            status=VersionStatus.draft.value,
            title=current.title,
            introduction=current.introduction,
            scope=current.scope,
            terms=current.terms,
            payment_terms=current.payment_terms,
            notes=current.notes,
            currency=current.currency,
            valid_until=current.valid_until,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(new_version)
        self.db.flush()

        for line in self._lines_for_version(current.id):
            self.db.add(
                CommercialProposalLine(
                    organization_id=organization_id,
                    proposal_version_id=new_version.id,
                    catalog_item_id=line.catalog_item_id,
                    source_opportunity_product_id=line.source_opportunity_product_id,
                    position=line.position,
                    name=line.name,
                    description=line.description,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    discount_type=line.discount_type,
                    discount_value=line.discount_value,
                    tax_rate=line.tax_rate,
                    subtotal=line.subtotal,
                    discount_amount=line.discount_amount,
                    tax_amount=line.tax_amount,
                    total=line.total,
                    metadata_json=dict(line.metadata_json or {}),
                )
            )
        self.db.flush()

        self._recompute_version_totals(new_version)
        proposal.current_version_id = new_version.id
        proposal.status = ProposalStatus.draft.value
        proposal.updated_by = user_id
        proposal.updated_at = now
        self._refresh_readiness(proposal, new_version)

        self._record_event(
            proposal,
            new_version,
            event_type=EventNames.SALES_PROPOSAL_VERSION_CREATED,
            title=f"Version {new_version.version_number} créée",
            payload={"version_number": new_version.version_number, "from_version": current.version_number},
            actor_user_id=user_id,
        )
        return new_version

    # ----------------------------------------------------------------- #
    # Lines
    # ----------------------------------------------------------------- #

    def add_line(
        self, *, organization_id: int, user_id: int | None, proposal_id: int, data: LineCreate
    ) -> CommercialProposalLine:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        self._require_editable(version)
        self._check_version_concurrency(version, data.expected_updated_at)

        position = data.position
        if position is None:
            existing = self._lines_for_version(version.id)
            position = (max((l.position for l in existing), default=-1)) + 1

        computed = compute_line_amounts(
            quantity=data.quantity,
            unit_price=data.unit_price,
            discount_type=data.discount_type.value,
            discount_value=data.discount_value,
            tax_rate=data.tax_rate,
        )
        line = CommercialProposalLine(
            organization_id=organization_id,
            proposal_version_id=version.id,
            catalog_item_id=data.catalog_item_id,
            position=position,
            name=data.name,
            description=data.description,
            quantity=qty(data.quantity),
            unit_price=money(data.unit_price),
            discount_type=data.discount_type.value,
            discount_value=money(data.discount_value),
            tax_rate=money(data.tax_rate),
            subtotal=computed["subtotal"],
            discount_amount=computed["discount_amount"],
            tax_amount=computed["tax_amount"],
            total=computed["total"],
        )
        self.db.add(line)
        self.db.flush()

        self._recompute_version_totals(version)
        self._refresh_readiness(proposal, version)
        proposal.updated_by = user_id
        proposal.updated_at = self._now()
        return line

    def update_line(
        self,
        *,
        organization_id: int,
        user_id: int | None,
        proposal_id: int,
        line_id: int,
        data: LineUpdate,
    ) -> CommercialProposalLine:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        self._require_editable(version)
        self._check_version_concurrency(version, data.expected_updated_at)
        line = self._get_line(version.id, line_id)

        if data.catalog_item_id is not None:
            line.catalog_item_id = data.catalog_item_id
        if data.name is not None:
            line.name = data.name
        if data.description is not None:
            line.description = data.description
        if data.position is not None:
            line.position = data.position

        quantity = data.quantity if data.quantity is not None else line.quantity
        unit_price = data.unit_price if data.unit_price is not None else line.unit_price
        discount_type = data.discount_type.value if data.discount_type is not None else line.discount_type
        discount_value = data.discount_value if data.discount_value is not None else line.discount_value
        tax_rate = data.tax_rate if data.tax_rate is not None else line.tax_rate

        computed = compute_line_amounts(
            quantity=quantity,
            unit_price=unit_price,
            discount_type=discount_type,
            discount_value=discount_value,
            tax_rate=tax_rate,
        )
        line.quantity = qty(quantity)
        line.unit_price = money(unit_price)
        line.discount_type = discount_type
        line.discount_value = money(discount_value)
        line.tax_rate = money(tax_rate)
        line.subtotal = computed["subtotal"]
        line.discount_amount = computed["discount_amount"]
        line.tax_amount = computed["tax_amount"]
        line.total = computed["total"]
        line.updated_at = self._now()

        self._recompute_version_totals(version)
        self._refresh_readiness(proposal, version)
        proposal.updated_by = user_id
        proposal.updated_at = self._now()
        return line

    def delete_line(
        self,
        *,
        organization_id: int,
        user_id: int | None,
        proposal_id: int,
        line_id: int,
        expected_updated_at: datetime | None = None,
    ) -> None:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        self._require_editable(version)
        self._check_version_concurrency(version, expected_updated_at)
        line = self._get_line(version.id, line_id)

        line.deleted_at = self._now()
        self._recompute_version_totals(version)
        self._refresh_readiness(proposal, version)
        proposal.updated_by = user_id
        proposal.updated_at = self._now()

    def _recompute_version_totals(self, version: CommercialProposalVersion) -> None:
        lines = self._lines_for_version(version.id)
        totals = sum_totals(
            [
                {
                    "subtotal": l.subtotal,
                    "discount_amount": l.discount_amount,
                    "tax_amount": l.tax_amount,
                    "total": l.total,
                }
                for l in lines
            ]
        )
        version.subtotal = totals["subtotal"]
        version.discount_total = totals["discount_total"]
        version.tax_total = totals["tax_total"]
        version.total = totals["total"]
        version.updated_at = self._now()
        self.db.flush()

    def _refresh_readiness(self, proposal: CommercialProposal, version: CommercialProposalVersion) -> None:
        company = None
        if proposal.sales_company_id:
            company = self.db.get(SalesCompany, proposal.sales_company_id)
        lines = self._lines_for_version(version.id)
        result = compute_readiness(
            has_company=proposal.sales_company_id is not None,
            has_contact=proposal.person_id is not None,
            has_address=bool(company and company.address_line and company.city),
            has_legal_id=bool(company and (company.siret or company.vat_number)),
            currency=version.currency or proposal.currency,
            lines_count=len(lines),
            lines_valid=lines_are_valid(lines),
            has_valid_until=bool(version.valid_until or proposal.valid_until),
            has_payment_terms=bool(version.payment_terms),
            has_terms=bool(version.terms),
            has_owner=proposal.owner_user_id is not None,
            has_current_version=proposal.current_version_id is not None,
            has_pdf=bool(version.pdf_vault_document_id),
            status=proposal.status,
        )
        version.readiness_score = result["score"]
        version.readiness_level = result["level"]
        version.readiness_explanation = result
        self.db.flush()

    # ----------------------------------------------------------------- #
    # Workflow
    # ----------------------------------------------------------------- #

    def _record_event(
        self,
        proposal: CommercialProposal,
        version: CommercialProposalVersion | None,
        *,
        event_type: str,
        title: str,
        payload: dict[str, Any],
        actor_user_id: int | None,
    ) -> CommercialProposalEvent:
        now = self._now()
        row = CommercialProposalEvent(
            organization_id=proposal.organization_id,
            proposal_id=proposal.id,
            version_id=version.id if version else None,
            event_type=event_type,
            title=title,
            payload=payload or {},
            actor_user_id=actor_user_id,
            occurred_at=now,
        )
        self.db.add(row)
        self.db.flush()
        publish_proposal_event(
            self.db,
            event_name=event_type,
            organization_id=proposal.organization_id,
            proposal_id=proposal.id,
            payload=payload or {},
            actor_user_id=actor_user_id,
            idempotency_key=f"sales_proposal:{event_type}:{proposal.id}:{version.id if version else 0}:{row.id}",
        )
        return row

    def _apply_transition(
        self,
        proposal: CommercialProposal,
        version: CommercialProposalVersion,
        target: ProposalStatus,
        *,
        actor_user_id: int | None,
        event_name: str,
        title: str,
        payload: dict[str, Any] | None = None,
    ) -> CommercialProposal:
        current = ProposalStatus(proposal.status)
        allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
        if target not in allowed:
            raise HTTPException(
                409,
                detail={
                    "code": "invalid_transition",
                    "message": f"Transition non autorisée : {current.value} → {target.value}",
                },
            )
        now = self._now()
        proposal.status = target.value
        proposal.updated_by = actor_user_id
        proposal.updated_at = now
        version.status = target.value
        version.updated_at = now

        if target == ProposalStatus.sent:
            version.sent_at = now
            version.locked_at = now
        elif target == ProposalStatus.viewed:
            version.viewed_at = now
        elif target == ProposalStatus.accepted:
            version.accepted_at = now
            proposal.accepted_at = now
        elif target == ProposalStatus.rejected:
            version.rejected_at = now
            proposal.rejected_at = now
        elif target == ProposalStatus.expired:
            proposal.expired_at = now

        self._refresh_readiness(proposal, version)
        self._record_event(
            proposal, version, event_type=event_name, title=title, payload=payload or {}, actor_user_id=actor_user_id
        )
        return proposal

    def prepare(self, *, organization_id: int, user_id: int | None, proposal_id: int) -> CommercialProposal:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        return self._apply_transition(
            proposal,
            version,
            ProposalStatus.preparing,
            actor_user_id=user_id,
            event_name=EVENT_PROPOSAL_PREPARING,
            title="Préparation démarrée",
        )

    def request_review(self, *, organization_id: int, user_id: int | None, proposal_id: int) -> CommercialProposal:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        return self._apply_transition(
            proposal,
            version,
            ProposalStatus.review_required,
            actor_user_id=user_id,
            event_name=EventNames.SALES_PROPOSAL_REVIEW_REQUESTED,
            title="Revue demandée",
        )

    def approve(self, *, organization_id: int, user_id: int | None, proposal_id: int) -> CommercialProposal:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        return self._apply_transition(
            proposal,
            version,
            ProposalStatus.approved,
            actor_user_id=user_id,
            event_name=EventNames.SALES_PROPOSAL_APPROVED,
            title="Proposition approuvée",
        )

    def mark_sent(self, *, organization_id: int, user_id: int | None, proposal_id: int) -> CommercialProposal:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        if ProposalStatus(proposal.status) != ProposalStatus.approved:
            raise HTTPException(
                409,
                detail={
                    "code": "invalid_state",
                    "message": "La proposition doit être approuvée avant d'être marquée comme envoyée",
                },
            )
        if not version.pdf_vault_document_id:
            raise HTTPException(
                409, detail={"code": "pdf_required", "message": "Le PDF doit être généré avant l'envoi"}
            )
        blockers = (version.readiness_explanation or {}).get("blockers") or []
        if blockers:
            raise HTTPException(
                409,
                detail={
                    "code": "readiness_blocked",
                    "message": "La proposition n'est pas prête à être envoyée",
                    "blockers": blockers,
                },
            )
        return self._apply_transition(
            proposal,
            version,
            ProposalStatus.sent,
            actor_user_id=user_id,
            event_name=EventNames.SALES_PROPOSAL_SENT,
            title="Proposition envoyée",
        )

    def mark_viewed(self, *, organization_id: int, user_id: int | None, proposal_id: int) -> CommercialProposal:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        return self._apply_transition(
            proposal,
            version,
            ProposalStatus.viewed,
            actor_user_id=user_id,
            event_name=EventNames.SALES_PROPOSAL_VIEWED,
            title="Proposition consultée",
        )

    def start_negotiation(self, *, organization_id: int, user_id: int | None, proposal_id: int) -> CommercialProposal:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        return self._apply_transition(
            proposal,
            version,
            ProposalStatus.negotiating,
            actor_user_id=user_id,
            event_name=EventNames.SALES_PROPOSAL_NEGOTIATION_STARTED,
            title="Négociation démarrée",
        )

    def accept(
        self, *, organization_id: int, user_id: int | None, proposal_id: int, data: AcceptIn
    ) -> CommercialProposal:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        return self._apply_transition(
            proposal,
            version,
            ProposalStatus.accepted,
            actor_user_id=user_id,
            event_name=EventNames.SALES_PROPOSAL_ACCEPTED,
            title="Proposition acceptée",
            payload={"comment": data.comment} if data.comment else {},
        )

    def reject(
        self, *, organization_id: int, user_id: int | None, proposal_id: int, data: RejectIn
    ) -> CommercialProposal:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        proposal.reject_reason = data.reason
        proposal.reject_comment = data.comment
        return self._apply_transition(
            proposal,
            version,
            ProposalStatus.rejected,
            actor_user_id=user_id,
            event_name=EventNames.SALES_PROPOSAL_REJECTED,
            title="Proposition rejetée",
            payload={"reason": data.reason, "comment": data.comment},
        )

    def expire(self, *, organization_id: int, user_id: int | None, proposal_id: int) -> CommercialProposal:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        return self._apply_transition(
            proposal,
            version,
            ProposalStatus.expired,
            actor_user_id=user_id,
            event_name=EventNames.SALES_PROPOSAL_EXPIRED,
            title="Proposition expirée",
        )

    def cancel(self, *, organization_id: int, user_id: int | None, proposal_id: int) -> CommercialProposal:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        return self._apply_transition(
            proposal,
            version,
            ProposalStatus.cancelled,
            actor_user_id=user_id,
            event_name=EVENT_PROPOSAL_CANCELLED,
            title="Proposition annulée",
        )

    # ----------------------------------------------------------------- #
    # PDF
    # ----------------------------------------------------------------- #

    def generate_pdf(
        self, *, organization_id: int, user_id: int | None, proposal_id: int
    ) -> CommercialProposalVersion:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        if version.status in self._locked_statuses() and version.pdf_vault_document_id:
            raise HTTPException(
                409,
                detail={
                    "code": "pdf_immutable",
                    "message": "Le PDF de cette version verrouillée existe déjà — créez une nouvelle version pour le régénérer",
                },
            )

        lines = self._lines_for_version(version.id)
        company = self.db.get(SalesCompany, proposal.sales_company_id) if proposal.sales_company_id else None
        person = self.db.get(SalesPerson, proposal.person_id) if proposal.person_id else None
        organization = self.db.get(Organization, organization_id)

        pdf_bytes = proposal_version_to_pdf(
            organization,
            proposal,
            version,
            lines,
            company_name=company.name if company else None,
            contact_name=f"{person.first_name} {person.last_name}".strip() if person else None,
        )

        filename = f"{proposal.proposal_number}-v{version.version_number}.pdf"
        vault_doc, _reused = archive_or_reuse_pdf(
            self.db,
            user_id=user_id or 0,
            organization_id=organization_id,
            document_type=VaultDocumentType.quote,
            document_number=proposal.proposal_number,
            filename=filename,
            content=pdf_bytes,
            amount_ht=version.subtotal,
            amount_vat=version.tax_total,
            amount_ttc=version.total,
            currency=(version.currency or proposal.currency or "EUR")[:3],
            customer_id=proposal.linked_customer_id,
            skip_access_check=True,
        )
        version.pdf_vault_document_id = vault_doc.id
        version.checksum = vault_doc.checksum_sha256
        version.updated_at = self._now()
        self._refresh_readiness(proposal, version)

        self._record_event(
            proposal,
            version,
            event_type=EventNames.SALES_PROPOSAL_PDF_GENERATED,
            title="PDF généré",
            payload={"version_number": version.version_number, "checksum": vault_doc.checksum_sha256},
            actor_user_id=user_id,
        )
        return version

    # ----------------------------------------------------------------- #
    # Workspace / diff / conversion
    # ----------------------------------------------------------------- #

    def _company_workspace(self, company: SalesCompany | None) -> dict[str, Any] | None:
        if not company:
            return None
        return {
            "id": company.id,
            "name": company.name,
            "siret": company.siret,
            "vat_number": company.vat_number,
            "email": company.email,
            "phone": company.phone,
            "address_line": company.address_line,
            "city": company.city,
            "postal_code": company.postal_code,
            "country": company.country,
        }

    def _contact_workspace(self, person: SalesPerson | None) -> dict[str, Any] | None:
        if not person:
            return None
        return {
            "id": person.id,
            "first_name": person.first_name,
            "last_name": person.last_name,
            "email": person.email,
            "phone": person.phone,
            "job_title": person.job_title,
        }

    def _opportunity_workspace(self, opportunity: SalesOpportunity | None) -> dict[str, Any] | None:
        if not opportunity:
            return None
        amount = opportunity.final_amount if opportunity.final_amount is not None else opportunity.estimated_amount
        return {
            "id": opportunity.id,
            "name": opportunity.name,
            "status": opportunity.status,
            "amount": amount,
        }

    def _version_payload(
        self, version: CommercialProposalVersion, lines: list[CommercialProposalLine]
    ) -> dict[str, Any]:
        return {
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

    def _compute_available_actions(
        self,
        proposal: CommercialProposal,
        version: CommercialProposalVersion,
        readiness: dict[str, Any],
    ) -> list[dict[str, Any]]:
        current = ProposalStatus(proposal.status)
        allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
        blockers = readiness.get("blockers") or []
        has_pdf = bool(version.pdf_vault_document_id)
        locked = version.status in self._locked_statuses()

        def transition_action(action_id: str, label: str, target: ProposalStatus) -> dict[str, Any]:
            enabled = target in allowed
            return {
                "id": action_id,
                "label": label,
                "kind": "action",
                "enabled": enabled,
                "reason": None if enabled else f"Non disponible depuis le statut « {current.value} »",
            }

        mark_sent_ready = ProposalStatus.sent in allowed and has_pdf and not blockers
        mark_sent_reason = None
        if not mark_sent_ready:
            if ProposalStatus.sent not in allowed:
                mark_sent_reason = f"Non disponible depuis le statut « {current.value} »"
            elif not has_pdf:
                mark_sent_reason = "Le PDF doit être généré au préalable"
            else:
                mark_sent_reason = "La proposition présente des blocages de préparation"

        return [
            transition_action("prepare", "Démarrer la préparation", ProposalStatus.preparing),
            transition_action("request_review", "Demander une revue", ProposalStatus.review_required),
            transition_action("approve", "Approuver", ProposalStatus.approved),
            {
                "id": "mark_sent",
                "label": "Marquer comme envoyée",
                "kind": "action",
                "enabled": mark_sent_ready,
                "reason": mark_sent_reason,
            },
            transition_action("mark_viewed", "Marquer comme consultée", ProposalStatus.viewed),
            transition_action("start_negotiation", "Démarrer la négociation", ProposalStatus.negotiating),
            transition_action("accept", "Accepter", ProposalStatus.accepted),
            transition_action("reject", "Rejeter", ProposalStatus.rejected),
            transition_action("expire", "Marquer comme expirée", ProposalStatus.expired),
            transition_action("cancel", "Annuler", ProposalStatus.cancelled),
            {
                "id": "generate_pdf",
                "label": "Générer le PDF",
                "kind": "action",
                "enabled": not (locked and has_pdf),
                "reason": None if not (locked and has_pdf) else "PDF déjà généré pour cette version verrouillée",
            },
            {
                "id": "new_version",
                "label": "Créer une nouvelle version",
                "kind": "action",
                "enabled": current not in (ProposalStatus.converted, ProposalStatus.cancelled),
                "reason": None,
            },
            {
                "id": "prepare_conversion",
                "label": "Préparer la conversion",
                "kind": "action",
                "enabled": current == ProposalStatus.accepted,
                "reason": None if current == ProposalStatus.accepted else "La proposition doit être acceptée",
                "disabled_reason": None
                if current == ProposalStatus.accepted
                else "La proposition doit être acceptée",
                "permission": "sales.proposals.convert",
                "requires_confirmation": False,
                "destructive": False,
                "expected_result": "conversion_state",
            },
            {
                "id": "select_existing_customer",
                "label": "Sélectionner un client existant",
                "kind": "action",
                "enabled": current == ProposalStatus.accepted and not proposal.linked_invoice_id,
                "reason": None
                if current == ProposalStatus.accepted and not proposal.linked_invoice_id
                else "Disponible uniquement sur proposition acceptée non convertie",
                "disabled_reason": None
                if current == ProposalStatus.accepted and not proposal.linked_invoice_id
                else "Disponible uniquement sur proposition acceptée non convertie",
                "permission": "sales.proposals.convert",
                "requires_confirmation": False,
                "destructive": False,
                "expected_result": "customer_linked",
            },
            {
                "id": "create_customer",
                "label": "Créer un client ComptaPilot",
                "kind": "action",
                "enabled": current == ProposalStatus.accepted and not proposal.linked_invoice_id,
                "reason": None
                if current == ProposalStatus.accepted and not proposal.linked_invoice_id
                else "Disponible uniquement sur proposition acceptée non convertie",
                "disabled_reason": None
                if current == ProposalStatus.accepted and not proposal.linked_invoice_id
                else "Disponible uniquement sur proposition acceptée non convertie",
                "permission": "invoice.create",
                "requires_confirmation": True,
                "destructive": False,
                "expected_result": "customer_created",
            },
            {
                "id": "refresh_conversion_preview",
                "label": "Actualiser l'aperçu facture",
                "kind": "action",
                "enabled": current in (ProposalStatus.accepted, ProposalStatus.converted),
                "reason": None
                if current in (ProposalStatus.accepted, ProposalStatus.converted)
                else "Proposition non acceptée",
                "disabled_reason": None
                if current in (ProposalStatus.accepted, ProposalStatus.converted)
                else "Proposition non acceptée",
                "permission": "sales.proposals.convert",
                "requires_confirmation": False,
                "destructive": False,
                "expected_result": "invoice_preview",
            },
            {
                "id": "convert_to_invoice",
                "label": "Créer la facture brouillon",
                "kind": "action",
                "enabled": current == ProposalStatus.accepted and not proposal.linked_invoice_id,
                "reason": None
                if current == ProposalStatus.accepted and not proposal.linked_invoice_id
                else (
                    "Proposition déjà convertie"
                    if current == ProposalStatus.converted or proposal.linked_invoice_id
                    else "La proposition doit être acceptée"
                ),
                "disabled_reason": None
                if current == ProposalStatus.accepted and not proposal.linked_invoice_id
                else (
                    "Proposition déjà convertie"
                    if current == ProposalStatus.converted or proposal.linked_invoice_id
                    else "La proposition doit être acceptée"
                ),
                "permission": "sales.proposals.convert",
                "requires_confirmation": True,
                "destructive": False,
                "expected_result": "draft_invoice",
            },
            {
                "id": "open_linked_customer",
                "label": "Ouvrir le client lié",
                "kind": "navigation",
                "enabled": bool(proposal.linked_customer_id),
                "reason": None if proposal.linked_customer_id else "Aucun client lié",
                "disabled_reason": None if proposal.linked_customer_id else "Aucun client lié",
                "permission": "sales.proposals.read",
                "requires_confirmation": False,
                "destructive": False,
                "expected_result": "navigate_customer",
            },
            {
                "id": "open_linked_invoice",
                "label": "Ouvrir la facture liée",
                "kind": "navigation",
                "enabled": bool(proposal.linked_invoice_id),
                "reason": None if proposal.linked_invoice_id else "Aucune facture liée",
                "disabled_reason": None if proposal.linked_invoice_id else "Aucune facture liée",
                "permission": "sales.proposals.read",
                "requires_confirmation": False,
                "destructive": False,
                "expected_result": "navigate_invoice",
            },
        ]

    def build_workspace(self, *, organization_id: int, proposal_id: int) -> dict[str, Any]:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._get_current_version(proposal)
        lines = self._lines_for_version(version.id)

        company = self.db.get(SalesCompany, proposal.sales_company_id) if proposal.sales_company_id else None
        person = self.db.get(SalesPerson, proposal.person_id) if proposal.person_id else None
        opportunity = (
            self.db.get(SalesOpportunity, proposal.opportunity_id) if proposal.opportunity_id else None
        )

        version_rows = (
            self.db.query(CommercialProposalVersion)
            .filter(
                CommercialProposalVersion.proposal_id == proposal.id,
                CommercialProposalVersion.deleted_at.is_(None),
            )
            .order_by(CommercialProposalVersion.version_number.desc())
            .all()
        )
        versions_summary = [
            {
                "id": v.id,
                "version_number": v.version_number,
                "status": v.status,
                "total": v.total,
                "created_at": v.created_at,
                "is_current": v.id == proposal.current_version_id,
            }
            for v in version_rows
        ]

        event_rows = (
            self.db.query(CommercialProposalEvent)
            .filter(CommercialProposalEvent.proposal_id == proposal.id)
            .order_by(CommercialProposalEvent.occurred_at.desc())
            .limit(50)
            .all()
        )
        timeline = [
            {
                "id": e.id,
                "event_type": e.event_type,
                "title": e.title,
                "occurred_at": e.occurred_at,
                "payload": e.payload or {},
            }
            for e in event_rows
        ]

        documents = [
            {
                "version_id": v.id,
                "version_number": v.version_number,
                "vault_document_id": str(v.pdf_vault_document_id) if v.pdf_vault_document_id else None,
                "checksum": v.checksum,
                "generated": bool(v.pdf_vault_document_id),
                "generated_at": v.updated_at if v.pdf_vault_document_id else None,
                "open_url": f"/vault?id={v.pdf_vault_document_id}" if v.pdf_vault_document_id else None,
                "label": f"PDF V{v.version_number}",
            }
            for v in version_rows
            if v.pdf_vault_document_id
        ]

        readiness = version.readiness_explanation or {}
        locked = version.status in self._locked_statuses()
        allowed_transitions = sorted(
            s.value for s in ALLOWED_TRANSITIONS.get(ProposalStatus(proposal.status), frozenset())
        )
        available_actions = self._compute_available_actions(proposal, version, readiness)

        can_convert = proposal.status == ProposalStatus.accepted.value
        conversion_reasons: list[str] = []
        if not can_convert:
            conversion_reasons.append("La proposition doit être acceptée pour être convertie")

        return {
            "header": {
                "proposal_id": proposal.id,
                "proposal_number": proposal.proposal_number,
                "proposal_type": proposal.proposal_type,
                "status": proposal.status,
                "title": version.title,
                "currency": proposal.currency,
                "valid_until": proposal.valid_until,
                "owner_user_id": proposal.owner_user_id,
                "created_at": proposal.created_at,
                "updated_at": proposal.updated_at,
                "company_name": company.name if company else None,
                "opportunity_id": proposal.opportunity_id,
                "opportunity_name": opportunity.name if opportunity else None,
                "version_number": version.version_number,
                "total": version.total,
            },
            "current_version": self._version_payload(version, lines),
            "versions": versions_summary,
            "lines": lines,
            "totals": {
                "subtotal": version.subtotal,
                "discount_total": version.discount_total,
                "tax_total": version.tax_total,
                "total": version.total,
                "currency": version.currency,
            },
            "readiness": {
                "score": version.readiness_score,
                "level": version.readiness_level,
                "checks": readiness.get("checks", []),
                "blockers": readiness.get("blockers", []),
                "warnings": readiness.get("warnings", []),
                "recommendations": readiness.get("recommendations", []),
            },
            "workflow": {
                "status": proposal.status,
                "version_status": version.status,
                "locked": locked,
                "allowed_transitions": allowed_transitions,
            },
            "company": self._company_workspace(company),
            "contact": self._contact_workspace(person),
            "opportunity": self._opportunity_workspace(opportunity),
            "documents": documents,
            "timeline": timeline,
            "available_actions": available_actions,
            "conversion_state": {
                "can_convert": can_convert,
                "linked_customer_id": proposal.linked_customer_id,
                "linked_invoice_id": proposal.linked_invoice_id,
                "conversion_status": getattr(proposal, "conversion_status", None)
                or ("converted" if proposal.linked_invoice_id else "not_ready"),
                "reasons": conversion_reasons,
            },
            "generated_at": self._now(),
        }

    def compare_versions(
        self, *, organization_id: int, proposal_id: int, from_version_id: int, to_version_id: int
    ) -> dict[str, Any]:
        proposal = self._get_proposal(organization_id, proposal_id)
        from_version = self._get_version(organization_id, proposal.id, from_version_id)
        to_version = self._get_version(organization_id, proposal.id, to_version_id)
        from_lines = self._lines_for_version(from_version.id)
        to_lines = self._lines_for_version(to_version.id)

        def version_dict(v: CommercialProposalVersion) -> dict[str, Any]:
            return {
                "version_number": v.version_number,
                "valid_until": str(v.valid_until) if v.valid_until else "",
                "terms": v.terms or "",
                "payment_terms": v.payment_terms or "",
                "notes": v.notes or "",
                "title": v.title or "",
                "introduction": v.introduction or "",
                "scope": v.scope or "",
                "total": v.total,
            }

        def line_dict(l: CommercialProposalLine) -> dict[str, Any]:
            return {
                "id": l.id,
                "source_key": l.source_opportunity_product_id or l.catalog_item_id or l.name,
                "name": l.name,
                "quantity": l.quantity,
                "unit_price": l.unit_price,
                "discount_type": l.discount_type,
                "discount_value": l.discount_value,
                "tax_rate": l.tax_rate,
                "total": l.total,
            }

        return diff_compare_versions(
            from_version=version_dict(from_version),
            to_version=version_dict(to_version),
            from_lines=[line_dict(l) for l in from_lines],
            to_lines=[line_dict(l) for l in to_lines],
        )

    def prepare_conversion_bridge(self, *, organization_id: int, proposal_id: int) -> dict[str, Any]:
        proposal = self._get_proposal(organization_id, proposal_id)
        return prepare_conversion(self.db, organization_id=organization_id, proposal=proposal)

    # ----------------------------------------------------------------- #
    # Opportunity amount sync (hybrid amount helper)
    # ----------------------------------------------------------------- #

    def sync_opportunity_amounts(
        self, *, organization_id: int, opportunity_id: int
    ) -> SalesOpportunity | None:
        opportunity = (
            self.db.query(SalesOpportunity)
            .filter(
                SalesOpportunity.id == opportunity_id,
                SalesOpportunity.organization_id == organization_id,
                SalesOpportunity.deleted_at.is_(None),
            )
            .first()
        )
        if not opportunity:
            return None
        products = (
            self.db.query(SalesOpportunityProduct)
            .filter(
                SalesOpportunityProduct.opportunity_id == opportunity_id,
                SalesOpportunityProduct.deleted_at.is_(None),
            )
            .all()
        )
        calculated = money(sum((p.line_total or Decimal("0") for p in products), Decimal("0")))
        opportunity.calculated_amount = calculated
        if (opportunity.amount_mode or AmountMode.calculated.value) == AmountMode.calculated.value:
            opportunity.final_amount = calculated
        final_amount = opportunity.final_amount if opportunity.final_amount is not None else calculated
        opportunity.amount_difference = money(final_amount - calculated)
        opportunity.updated_at = self._now()
        self.db.flush()
        return opportunity
