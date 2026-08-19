"""Proposal → Invoice conversion bridge (S1.6.1).

Controlled human conversion: accepted proposal → draft ComptaPilot invoice.
Never auto-sends. Never silently creates customers. Idempotent.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.events.event_types import EventNames
from app.models_saas import Customer, SalesDocument
from app.sales_crm.models import SalesCompany, SalesPerson
from app.sales_proposals.conversion import prepare_conversion
from app.sales_proposals.enums import LOCKED_VERSION_STATUSES, ProposalStatus, VersionStatus
from app.sales_proposals.events import publish_proposal_event
from app.sales_proposals.models import (
    CommercialProposal,
    CommercialProposalEvent,
    CommercialProposalLine,
    CommercialProposalVersion,
)
from app.services.billing import create_sales_document

TWO = Decimal("0.01")
TOLERANCE = Decimal("0.02")

CustomerResolutionMode = Literal[
    "use_linked_customer",
    "use_existing_customer",
    "create_new_customer",
]

ConversionStatus = Literal[
    "not_ready",
    "customer_required",
    "customer_ambiguous",
    "ready",
    "converting",
    "converted",
    "failed",
]


def _now() -> datetime:
    return datetime.utcnow()


def _money(v: Any) -> Decimal:
    return Decimal(str(v or 0)).quantize(TWO, rounding=ROUND_HALF_UP)


class ProposalInvoiceConversionService:
    def __init__(self, db: Session):
        self.db = db

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
            raise HTTPException(404, detail={"code": "not_found", "message": "Proposition introuvable"})
        return row

    def _accepted_version(self, proposal: CommercialProposal) -> CommercialProposalVersion:
        if not proposal.current_version_id:
            raise HTTPException(
                409,
                detail={"code": "no_version", "message": "Version acceptée introuvable"},
            )
        version = (
            self.db.query(CommercialProposalVersion)
            .filter(
                CommercialProposalVersion.id == proposal.current_version_id,
                CommercialProposalVersion.proposal_id == proposal.id,
                CommercialProposalVersion.deleted_at.is_(None),
            )
            .first()
        )
        if not version:
            raise HTTPException(
                409,
                detail={"code": "no_version", "message": "Version acceptée introuvable"},
            )
        return version

    def _lines(self, version_id: int) -> list[CommercialProposalLine]:
        return (
            self.db.query(CommercialProposalLine)
            .filter(
                CommercialProposalLine.proposal_version_id == version_id,
                CommercialProposalLine.deleted_at.is_(None),
            )
            .order_by(CommercialProposalLine.position.asc(), CommercialProposalLine.id.asc())
            .all()
        )

    def _record_event(
        self,
        proposal: CommercialProposal,
        version: CommercialProposalVersion | None,
        *,
        event_type: str,
        title: str,
        payload: dict[str, Any],
        actor_user_id: int | None,
    ) -> None:
        self.db.add(
            CommercialProposalEvent(
                organization_id=proposal.organization_id,
                proposal_id=proposal.id,
                version_id=version.id if version else None,
                event_type=event_type,
                title=title,
                payload=payload,
                actor_user_id=actor_user_id,
                occurred_at=_now(),
            )
        )

    def build_conversion_state(
        self, *, organization_id: int, proposal_id: int
    ) -> dict[str, Any]:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._accepted_version(proposal)
        prep = prepare_conversion(self.db, organization_id=organization_id, proposal=proposal)

        blockers: list[str] = []
        warnings: list[str] = list(prep.get("missing_information") or [])
        conversion_status: ConversionStatus = "not_ready"
        can_convert = False

        if proposal.linked_invoice_id or proposal.status == ProposalStatus.converted.value:
            conversion_status = "converted"
            can_convert = False
            blockers.append("Proposition déjà convertie")
        elif proposal.status != ProposalStatus.accepted.value:
            conversion_status = "not_ready"
            blockers.append("La proposition doit être acceptée")
        else:
            duplicates = prep.get("duplicate_candidates") or {}
            exact = duplicates.get("exact_match") or []
            possible = duplicates.get("possible_match") or []
            if proposal.linked_customer_id:
                conversion_status = "ready"
                can_convert = True
            elif exact and not possible:
                conversion_status = "ready"
                can_convert = False  # must select explicitly
                warnings.append("Correspondance exacte détectée — sélectionnez le client")
            elif possible or exact:
                conversion_status = "customer_ambiguous"
                blockers.append("Client ambigu — sélectionnez ou créez un client")
            else:
                conversion_status = "customer_required"
                blockers.append("Client ComptaPilot requis")

            if not self._lines(version.id):
                blockers.append("Aucune ligne sur la version acceptée")
                can_convert = False
                conversion_status = "not_ready"

        if proposal.conversion_status == "failed":
            conversion_status = "failed"
            if proposal.conversion_error_code:
                warnings.append(f"Dernière erreur: {proposal.conversion_error_code}")

        return {
            "proposal_id": proposal.id,
            "proposal_status": proposal.status,
            "accepted_version_id": version.id,
            "conversion_status": conversion_status,
            "linked_customer_id": proposal.linked_customer_id,
            "linked_invoice_id": proposal.linked_invoice_id,
            "customer_resolution": {
                "linked_customer": prep.get("linked_customer"),
                "modes": [
                    "use_linked_customer",
                    "use_existing_customer",
                    "create_new_customer",
                ],
            },
            "duplicate_candidates": prep.get("duplicate_candidates") or {},
            "missing_information": prep.get("missing_information") or [],
            "preview_available": proposal.status == ProposalStatus.accepted.value,
            "can_convert": can_convert and not blockers,
            "blockers": blockers,
            "warnings": warnings,
            "generated_at": _now(),
        }

    def build_invoice_preview(
        self,
        *,
        organization_id: int,
        proposal_id: int,
        customer_id: int | None = None,
    ) -> dict[str, Any]:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._accepted_version(proposal)
        if proposal.status != ProposalStatus.accepted.value and proposal.status != ProposalStatus.converted.value:
            raise HTTPException(
                409,
                detail={"code": "not_accepted", "message": "La proposition n'est pas acceptée"},
            )

        cid = customer_id or proposal.linked_customer_id
        customer = None
        if cid:
            customer = self.db.get(Customer, cid)
            if not customer or customer.organization_id != organization_id:
                raise HTTPException(
                    403,
                    detail={"code": "customer_org", "message": "Client hors organisation"},
                )

        lines = self._lines(version.id)
        mapped_lines, totals = self._map_lines(lines)
        blockers: list[str] = []
        warnings: list[str] = []
        if not customer:
            blockers.append("Client requis pour confirmer")
        if not mapped_lines:
            blockers.append("Aucune ligne à facturer")
        if proposal.linked_invoice_id:
            blockers.append("Facture déjà liée")

        # ComptaPilot SalesDocument uses a single document-level vat_rate.
        # Never silently collapse multi-rate proposals to the first line rate.
        distinct_rates = {
            round(float(line.get("vat_rate") or 0), 4) for line in mapped_lines
        }
        if len(distinct_rates) > 1:
            blockers.append(
                "TVA multi-taux non supportée pour la conversion ComptaPilot. "
                "Harmonisez les taux de la proposition (un seul taux) avant conversion."
            )

        # Financial revalidation
        expected_ttc = _money(version.total)
        preview_ttc = totals["total"]
        if abs(expected_ttc - preview_ttc) > TOLERANCE:
            blockers.append(
                f"Écart financier hors tolérance ({expected_ttc} vs {preview_ttc})"
            )

        return {
            "proposal": {
                "id": proposal.id,
                "proposal_number": proposal.proposal_number,
                "status": proposal.status,
            },
            "accepted_version": {
                "id": version.id,
                "version_number": version.version_number,
                "title": version.title,
                "locked_at": version.locked_at,
            },
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
            }
            if customer
            else None,
            "invoice_header": {
                "doc_type": "facture",
                "status": "draft",
                "currency": proposal.currency or "EUR",
                "customer_name": customer.name if customer else None,
                "source_type": "sales_proposal",
                "source_number": proposal.proposal_number,
                "payment_terms": version.payment_terms,
                "notes": version.notes,
            },
            "invoice_lines": mapped_lines,
            "subtotal": str(totals["subtotal"]),
            "discount_total": str(totals["discount_total"]),
            "tax_total": str(totals["tax_total"]),
            "total": str(totals["total"]),
            "currency": proposal.currency or "EUR",
            "payment_terms": version.payment_terms,
            "notes": version.notes,
            "warnings": warnings,
            "blockers": blockers,
            "multi_vat_rates": sorted(distinct_rates),
            "source_mapping": {
                "proposal_id": proposal.id,
                "version_id": version.id,
                "version_number": version.version_number,
            },
            "can_confirm": not blockers and customer is not None,
            "linked_invoice_id": proposal.linked_invoice_id,
        }

    def _map_lines(
        self, lines: list[CommercialProposalLine]
    ) -> tuple[list[dict[str, Any]], dict[str, Decimal]]:
        mapped: list[dict[str, Any]] = []
        subtotal = Decimal("0")
        discount_total = Decimal("0")
        tax_total = Decimal("0")
        total = Decimal("0")
        for line in lines:
            net = _money(line.subtotal) - _money(line.discount_amount)
            mapped.append(
                {
                    "description": line.name,
                    "detail": line.description,
                    "quantity": float(line.quantity),
                    "unit_price": float(line.unit_price),
                    "discount_type": line.discount_type,
                    "discount_value": float(line.discount_value),
                    "vat_rate": float(line.tax_rate),
                    "amount_ht": float(net),
                    "source_line_id": line.id,
                }
            )
            subtotal += _money(line.subtotal)
            discount_total += _money(line.discount_amount)
            tax_total += _money(line.tax_amount)
            total += _money(line.total)
        return mapped, {
            "subtotal": _money(subtotal),
            "discount_total": _money(discount_total),
            "tax_total": _money(tax_total),
            "total": _money(total),
        }

    def link_or_create_customer(
        self,
        *,
        organization_id: int,
        proposal_id: int,
        user_id: int | None,
        mode: CustomerResolutionMode,
        customer_id: int | None = None,
        customer_payload: dict[str, Any] | None = None,
        confirm_possible_match: bool = False,
    ) -> dict[str, Any]:
        proposal = self._get_proposal(organization_id, proposal_id)
        version = self._accepted_version(proposal)
        if proposal.status != ProposalStatus.accepted.value:
            raise HTTPException(
                409,
                detail={"code": "not_accepted", "message": "Proposition non acceptée"},
            )

        if mode == "use_linked_customer":
            if not proposal.linked_customer_id:
                raise HTTPException(
                    400,
                    detail={"code": "no_linked_customer", "message": "Aucun client déjà lié"},
                )
            customer = self.db.get(Customer, proposal.linked_customer_id)
            if not customer or customer.organization_id != organization_id:
                raise HTTPException(
                    403,
                    detail={"code": "customer_org", "message": "Client hors organisation"},
                )
            return {"customer": {"id": customer.id, "name": customer.name}, "created": False}

        if mode == "use_existing_customer":
            if not customer_id:
                raise HTTPException(
                    400,
                    detail={"code": "customer_required", "message": "customer_id requis"},
                )
            customer = self.db.get(Customer, customer_id)
            if not customer or customer.organization_id != organization_id:
                raise HTTPException(
                    403,
                    detail={"code": "customer_org", "message": "Client hors organisation"},
                )
            prep = prepare_conversion(self.db, organization_id=organization_id, proposal=proposal)
            possible = (prep.get("duplicate_candidates") or {}).get("possible_match") or []
            if possible and not confirm_possible_match:
                # still allow if exact or explicit — require confirm for possible
                is_possible = any(
                    (c.get("record") or {}).get("id") == customer_id for c in possible
                )
                if is_possible:
                    raise HTTPException(
                        409,
                        detail={
                            "code": "possible_match_confirmation_required",
                            "message": "Confirmez la sélection d'une correspondance possible",
                        },
                    )
            proposal.linked_customer_id = customer.id
            proposal.updated_at = _now()
            if proposal.sales_company_id:
                company = self.db.get(SalesCompany, proposal.sales_company_id)
                if company and company.organization_id == organization_id:
                    company.linked_customer_id = customer.id
            self._record_event(
                proposal,
                version,
                event_type=EventNames.SALES_PROPOSAL_CUSTOMER_LINKED,
                title="Client ComptaPilot lié",
                payload={"customer_id": customer.id},
                actor_user_id=user_id,
            )
            publish_proposal_event(
                self.db,
                event_name=EventNames.SALES_PROPOSAL_CUSTOMER_LINKED,
                organization_id=organization_id,
                proposal_id=proposal.id,
                payload={"proposal_id": proposal.id, "customer_id": customer.id},
                actor_user_id=user_id,
                idempotency_key=f"sales:proposal:customer:linked:{proposal.id}:{customer.id}",
            )
            self.db.flush()
            return {"customer": {"id": customer.id, "name": customer.name}, "created": False}

        # create_new_customer
        payload = customer_payload or {}
        name = (payload.get("name") or "").strip()
        if not name:
            # derive from company
            if proposal.sales_company_id:
                company = self.db.get(SalesCompany, proposal.sales_company_id)
                if company:
                    name = company.name
                    payload.setdefault("email", company.email or "")
                    payload.setdefault("phone", company.phone or "")
                    payload.setdefault("vat_number", company.vat_number or company.siret or "")
                    addr = " ".join(
                        p
                        for p in [
                            company.address_line,
                            company.postal_code,
                            company.city,
                        ]
                        if p
                    )
                    payload.setdefault("address", addr)
        if not name:
            raise HTTPException(
                400,
                detail={"code": "name_required", "message": "Nom client requis"},
            )

        # final duplicate check
        prep = prepare_conversion(self.db, organization_id=organization_id, proposal=proposal)
        exact = (prep.get("duplicate_candidates") or {}).get("exact_match") or []
        if exact and not payload.get("force_create"):
            raise HTTPException(
                409,
                detail={
                    "code": "exact_duplicate",
                    "message": "Doublon exact détecté — sélectionnez le client existant",
                    "candidates": exact,
                },
            )

        customer = Customer(
            organization_id=organization_id,
            name=name,
            email=(payload.get("email") or "").strip(),
            phone=(payload.get("phone") or "").strip(),
            address=(payload.get("address") or "").strip(),
            vat_number=(payload.get("vat_number") or "").strip(),
        )
        self.db.add(customer)
        self.db.flush()
        proposal.linked_customer_id = customer.id
        proposal.updated_at = _now()
        if proposal.sales_company_id:
            company = self.db.get(SalesCompany, proposal.sales_company_id)
            if company and company.organization_id == organization_id:
                company.linked_customer_id = customer.id
        self._record_event(
            proposal,
            version,
            event_type=EventNames.SALES_PROPOSAL_CUSTOMER_CREATED,
            title="Client ComptaPilot créé depuis SalesPilot",
            payload={"customer_id": customer.id},
            actor_user_id=user_id,
        )
        publish_proposal_event(
            self.db,
            event_name=EventNames.SALES_PROPOSAL_CUSTOMER_CREATED,
            organization_id=organization_id,
            proposal_id=proposal.id,
            payload={"proposal_id": proposal.id, "customer_id": customer.id},
            actor_user_id=user_id,
            idempotency_key=f"sales:proposal:customer:created:{proposal.id}:{customer.id}",
        )
        self.db.flush()
        return {"customer": {"id": customer.id, "name": customer.name}, "created": True}

    def convert_to_invoice(
        self,
        *,
        organization_id: int,
        proposal_id: int,
        user_id: int | None,
        customer_resolution_mode: CustomerResolutionMode,
        customer_id: int | None = None,
        customer_payload: dict[str, Any] | None = None,
        accepted_version_id: int | None = None,
        expected_proposal_updated_at: datetime | None = None,
        idempotency_key: str | None = None,
        confirm_possible_match: bool = False,
    ) -> dict[str, Any]:
        proposal = self._get_proposal(organization_id, proposal_id)

        # Idempotence: already converted
        if proposal.linked_invoice_id or proposal.status == ProposalStatus.converted.value:
            invoice = (
                self.db.get(SalesDocument, proposal.linked_invoice_id)
                if proposal.linked_invoice_id
                else None
            )
            if not invoice:
                raise HTTPException(
                    409,
                    detail={
                        "code": "orphan_invoice_link",
                        "message": "Lien facture orphelin — récupération manuelle requise",
                    },
                )
            return {
                "already_converted": True,
                "proposal_id": proposal.id,
                "invoice_id": invoice.id,
                "invoice_number": invoice.number,
                "invoice_status": invoice.status,
                "customer_id": proposal.linked_customer_id,
            }

        if idempotency_key and proposal.conversion_idempotency_key == idempotency_key:
            if proposal.linked_invoice_id:
                invoice = self.db.get(SalesDocument, proposal.linked_invoice_id)
                if invoice:
                    return {
                        "already_converted": True,
                        "proposal_id": proposal.id,
                        "invoice_id": invoice.id,
                        "invoice_number": invoice.number,
                        "invoice_status": invoice.status,
                        "customer_id": proposal.linked_customer_id,
                    }

        if expected_proposal_updated_at and proposal.updated_at:
            # tolerate microsecond/isoformat drift
            exp = expected_proposal_updated_at.replace(tzinfo=None)
            cur = proposal.updated_at.replace(tzinfo=None) if proposal.updated_at.tzinfo else proposal.updated_at
            if abs((cur - exp).total_seconds()) > 1:
                raise HTTPException(
                    409,
                    detail={
                        "code": "stale_proposal",
                        "message": "Proposition modifiée dans un autre onglet — rafraîchissez",
                    },
                )

        if proposal.status != ProposalStatus.accepted.value:
            raise HTTPException(
                409,
                detail={"code": "not_accepted", "message": "La proposition doit être acceptée"},
            )

        version = self._accepted_version(proposal)
        if accepted_version_id and accepted_version_id != version.id:
            raise HTTPException(
                409,
                detail={
                    "code": "version_mismatch",
                    "message": "La version acceptée a changé",
                },
            )
        if version.status not in {s.value for s in LOCKED_VERSION_STATUSES} and version.status != VersionStatus.accepted.value:
            # still allow if accepted at proposal level
            pass

        # Resolve customer
        resolved = self.link_or_create_customer(
            organization_id=organization_id,
            proposal_id=proposal_id,
            user_id=user_id,
            mode=customer_resolution_mode,
            customer_id=customer_id,
            customer_payload=customer_payload,
            confirm_possible_match=confirm_possible_match,
        )
        customer = self.db.get(Customer, resolved["customer"]["id"])
        assert customer is not None

        preview = self.build_invoice_preview(
            organization_id=organization_id,
            proposal_id=proposal_id,
            customer_id=customer.id,
        )
        if not preview["can_confirm"]:
            blockers = preview.get("blockers") or []
            if any("multi-taux" in str(b).lower() for b in blockers):
                raise HTTPException(
                    409,
                    detail={
                        "code": "multi_vat_unsupported",
                        "message": (
                            "TVA multi-taux non supportée pour la conversion ComptaPilot. "
                            "Harmonisez les taux avant conversion."
                        ),
                        "blockers": blockers,
                        "multi_vat_rates": preview.get("multi_vat_rates") or [],
                    },
                )
            raise HTTPException(
                409,
                detail={
                    "code": "preview_blocked",
                    "message": "Conversion bloquée",
                    "blockers": blockers,
                },
            )

        proposal.conversion_status = "converting"
        proposal.conversion_started_at = _now()
        proposal.conversion_idempotency_key = idempotency_key or proposal.conversion_idempotency_key
        proposal.conversion_error_code = None
        self.db.flush()

        publish_proposal_event(
            self.db,
            event_name=EventNames.SALES_PROPOSAL_CONVERSION_STARTED,
            organization_id=organization_id,
            proposal_id=proposal.id,
            payload={
                "proposal_id": proposal.id,
                "proposal_version_id": version.id,
                "customer_id": customer.id,
                "status": "converting",
            },
            actor_user_id=user_id,
            idempotency_key=f"sales:proposal:conversion:started:{proposal.id}:{version.id}",
        )

        lines = preview["invoice_lines"]
        # ComptaPilot create uses amount_ht + single vat_rate — only after multi-rate blocker passed
        amount_ht = float(_money(preview["subtotal"]) - _money(preview["discount_total"]))
        vat_rate = 20.0
        if lines:
            vat_rate = float(lines[0].get("vat_rate") or 20.0)
        # Safety: never convert if preview still reports multi-rate (defense in depth)
        rates = {round(float(l.get("vat_rate") or 0), 4) for l in lines}
        if len(rates) > 1:
            raise HTTPException(
                409,
                detail={
                    "code": "multi_vat_unsupported",
                    "message": (
                        "TVA multi-taux non supportée pour la conversion ComptaPilot. "
                        "Harmonisez les taux avant conversion."
                    ),
                    "blockers": preview["blockers"],
                },
            )

        try:
            # Unique source check
            existing = (
                self.db.query(SalesDocument)
                .filter(
                    SalesDocument.organization_id == organization_id,
                    SalesDocument.source_type == "sales_proposal",
                    SalesDocument.source_id == str(proposal.id),
                )
                .first()
            )
            if existing:
                proposal.linked_invoice_id = existing.id
                proposal.status = ProposalStatus.converted.value
                proposal.converted_at = _now()
                proposal.conversion_status = "converted"
                proposal.conversion_completed_at = _now()
                self.db.flush()
                return {
                    "already_converted": True,
                    "proposal_id": proposal.id,
                    "invoice_id": existing.id,
                    "invoice_number": existing.number,
                    "invoice_status": existing.status,
                    "customer_id": customer.id,
                }

            notes = (
                f"Source SalesPilot {proposal.proposal_number} V{version.version_number}"
                + (f"\n{version.notes}" if version.notes else "")
            )
            invoice = create_sales_document(
                self.db,
                organization_id=organization_id,
                doc_type="facture",
                customer_name=customer.name,
                customer_id=customer.id,
                customer_email=customer.email or "",
                amount_ht=amount_ht,
                vat_rate=vat_rate,
                lines=lines,
                notes=notes,
                commit=False,
                source_type="sales_proposal",
                source_id=str(proposal.id),
                source_version_id=str(version.id),
                source_number=proposal.proposal_number,
            )
            # Re-validate TTC tolerance against ComptaPilot float calc
            expected_ttc = _money(preview["total"])
            actual_ttc = _money(invoice.amount_ttc)
            if abs(expected_ttc - actual_ttc) > TOLERANCE:
                raise HTTPException(
                    409,
                    detail={
                        "code": "financial_mismatch",
                        "message": "Écart financier hors tolérance après calcul ComptaPilot",
                        "expected": str(expected_ttc),
                        "actual": str(actual_ttc),
                    },
                )

            proposal.linked_invoice_id = invoice.id
            proposal.linked_customer_id = customer.id
            proposal.status = ProposalStatus.converted.value
            proposal.converted_at = _now()
            proposal.conversion_status = "converted"
            proposal.conversion_completed_at = _now()
            proposal.updated_at = _now()
            proposal.updated_by = user_id

            self._record_event(
                proposal,
                version,
                event_type=EventNames.SALES_PROPOSAL_CONVERTED,
                title=f"Facture brouillon créée — {invoice.number}",
                payload={
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.number,
                    "customer_id": customer.id,
                },
                actor_user_id=user_id,
            )
            publish_proposal_event(
                self.db,
                event_name=EventNames.SALES_PROPOSAL_CONVERTED,
                organization_id=organization_id,
                proposal_id=proposal.id,
                payload={
                    "proposal_id": proposal.id,
                    "proposal_version_id": version.id,
                    "customer_id": customer.id,
                    "invoice_id": invoice.id,
                    "status": "converted",
                },
                actor_user_id=user_id,
                idempotency_key=f"sales:proposal:converted:{proposal.id}:{invoice.id}",
            )
            publish_proposal_event(
                self.db,
                event_name=EventNames.BILLING_INVOICE_CREATED_FROM_PROPOSAL,
                organization_id=organization_id,
                proposal_id=proposal.id,
                payload={
                    "proposal_id": proposal.id,
                    "proposal_version_id": version.id,
                    "customer_id": customer.id,
                    "invoice_id": invoice.id,
                    "status": "draft",
                },
                actor_user_id=user_id,
                idempotency_key=f"billing:invoice:from_proposal:{proposal.id}:{invoice.id}",
            )
            self.db.flush()
            return {
                "already_converted": False,
                "proposal_id": proposal.id,
                "invoice_id": invoice.id,
                "invoice_number": invoice.number,
                "invoice_status": invoice.status,
                "customer_id": customer.id,
                "message": "Facture brouillon créée — non envoyée",
            }
        except HTTPException as exc:
            proposal.conversion_status = "failed"
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            proposal.conversion_error_code = detail.get("code") if isinstance(detail, dict) else "http_error"
            self.db.flush()
            publish_proposal_event(
                self.db,
                event_name=EventNames.SALES_PROPOSAL_CONVERSION_FAILED,
                organization_id=organization_id,
                proposal_id=proposal.id,
                payload={
                    "proposal_id": proposal.id,
                    "proposal_version_id": version.id,
                    "customer_id": customer.id if customer else None,
                    "status": "failed",
                    "error_code": proposal.conversion_error_code,
                },
                actor_user_id=user_id,
                idempotency_key=f"sales:proposal:conversion:failed:{proposal.id}:{proposal.conversion_error_code}",
            )
            raise
        except Exception:
            proposal.conversion_status = "failed"
            proposal.conversion_error_code = "unexpected_error"
            self.db.flush()
            publish_proposal_event(
                self.db,
                event_name=EventNames.SALES_PROPOSAL_CONVERSION_FAILED,
                organization_id=organization_id,
                proposal_id=proposal.id,
                payload={
                    "proposal_id": proposal.id,
                    "status": "failed",
                    "error_code": "unexpected_error",
                },
                actor_user_id=user_id,
                idempotency_key=f"sales:proposal:conversion:failed:{proposal.id}:unexpected",
            )
            raise HTTPException(
                500,
                detail={
                    "code": "conversion_failed",
                    "message": "Échec de création de la facture — proposition restée acceptée",
                },
            )
