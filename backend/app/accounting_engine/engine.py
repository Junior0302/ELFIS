"""AccountingEngine — pipeline V2 de génération de propositions."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.accounting_engine.account_resolver import AccountResolver
from app.accounting_engine.confidence_engine import ConfidenceEngine
from app.accounting_engine.consistency_engine import ConsistencyEngine
from app.accounting_engine.enums import DocumentDirection, ProposalV2Status
from app.accounting_engine.journal_resolver import JournalResolver
from app.accounting_engine.learning import LearningEngine
from app.accounting_engine.rule_engine import RuleEngine
from app.accounting_engine.vat_engine import VATEngine
from app.agents.mapper import map_accounting
from app.schemas import ExtractionResult


class AccountingEngine:
    """
    Pipeline :
    données métier → règles → comptes → TVA → journal → lignes → contrôles → score.
    Aucune écriture définitive.
    """

    def __init__(self, db: Session):
        self._db = db
        self._rules = RuleEngine()
        self._accounts = AccountResolver(db)
        self._vat = VATEngine()
        self._journals = JournalResolver()
        self._consistency = ConsistencyEngine()
        self._confidence = ConfidenceEngine()
        self._learning = LearningEngine(db)

    def generate(
        self,
        *,
        organization_id: int,
        payload: dict[str, Any],
        extraction_quality: float | None = None,
        validation_quality: float | None = None,
    ) -> dict[str, Any]:
        self._accounts.ensure_default_pcg(organization_id)

        rules = self._rules.analyze(payload)
        party = (
            payload.get("supplier_name")
            or (payload.get("supplier") or {}).get("name")
            if isinstance(payload.get("supplier"), dict)
            else payload.get("supplier")
        ) or payload.get("customer_name")

        learning_hints = self._learning.lookup(
            organization_id=organization_id,
            direction=rules.direction,
            document_type=rules.document_type,
            party_name=str(party) if party else None,
        )

        intel_hints = payload.get("intelligence_account_hints") or {}
        similarity_hints = payload.get("similarity_account_hints") or {}
        ai_hints = payload.get("ai_account_hints") or {}

        accounts = self._accounts.resolve(
            organization_id=organization_id,
            direction=rules.direction,
            document_type=rules.document_type,
            rule_hints=rules.account_hints,
            learning_hints=learning_hints,
            similarity_hints=similarity_hints if isinstance(similarity_hints, dict) else {},
            ai_hints=ai_hints if isinstance(ai_hints, dict) else {},
            recommendation_hints=intel_hints if isinstance(intel_hints, dict) else {},
        )

        amounts = payload.get("amounts") if isinstance(payload.get("amounts"), dict) else {}
        vat_res = self._vat.compute(
            amount_ht=payload.get("amount_ht")
            or amounts.get("subtotal_excluding_tax"),
            amount_vat=payload.get("amount_vat")
            or amounts.get("total_tax")
            or payload.get("amount_tva"),
            amount_ttc=payload.get("amount_ttc")
            or amounts.get("total_including_tax"),
            vat_rate=payload.get("vat_rate") or amounts.get("vat_rate"),
            exempt=rules.exempt_vat,
        )

        journal = self._journals.resolve(
            direction=rules.direction,
            document_type=rules.document_type,
            preferred_journal=payload.get("preferred_journal")
            or learning_hints.get("journal"),
        )

        lines, explanation = self._build_lines(
            payload=payload,
            direction=rules.direction,
            document_type=rules.document_type,
            accounts=accounts.to_dict(),
            vat=vat_res,
            journal_code=journal.code,
        )

        cons = self._consistency.check(
            lines=lines,
            amount_ht=vat_res.amount_ht,
            amount_vat=vat_res.amount_vat,
            amount_ttc=vat_res.amount_ttc,
            currency=payload.get("currency") or "EUR",
            document_date=payload.get("document_date")
            or payload.get("invoice_date"),
            accounts=[
                accounts.expense_or_revenue,
                accounts.vat_account,
                accounts.third_party,
            ],
        )

        conf = self._confidence.score(
            extraction_quality=extraction_quality
            or payload.get("extraction_confidence"),
            validation_quality=validation_quality
            or payload.get("validation_confidence"),
            history_hit=bool(learning_hints),
            rules_applied=bool(rules.applied),
            consistency_ok=cons.ok,
            warning_count=len(vat_res.warnings) + len(cons.warnings) + len(accounts.warnings),
            error_count=len(vat_res.errors) + len(cons.errors),
            similarity_score=payload.get("similarity_score"),
            learning_score=0.9 if learning_hints else payload.get("learning_score"),
            ai_score=payload.get("ai_score"),
        )

        warnings = list(vat_res.warnings) + list(cons.warnings) + list(accounts.warnings)
        errors = list(vat_res.errors) + list(cons.errors)
        status = (
            ProposalV2Status.REQUIRES_REVIEW.value
            if errors or conf.score < 0.55 or not cons.balanced
            else ProposalV2Status.GENERATED.value
        )

        return {
            "status": status,
            "direction": rules.direction,
            "document_type": rules.document_type,
            "journal_code": journal.code,
            "journal_label": journal.label,
            "lines": lines,
            "amount_ht": float(vat_res.amount_ht),
            "amount_vat": float(vat_res.amount_vat),
            "amount_ttc": float(vat_res.amount_ttc),
            "vat_rate": float(vat_res.vat_rate) if vat_res.vat_rate is not None else None,
            "currency": payload.get("currency") or "EUR",
            "warnings": warnings,
            "errors": errors,
            "comments": rules.applied,
            "explanations": [
                explanation,
                journal.reason,
                f"comptes:{accounts.sources}",
            ],
            "consistency": cons.to_dict(),
            "confidence_score": conf.score,
            "confidence_detail": conf.to_dict(),
            "accounts": accounts.to_dict(),
            "rules": rules.to_dict(),
            "learning_applied": bool(learning_hints),
        }

    def _build_lines(
        self,
        *,
        payload: dict[str, Any],
        direction: str,
        document_type: str,
        accounts: dict[str, Any],
        vat: Any,
        journal_code: str,
    ) -> tuple[list[dict[str, Any]], str]:
        """Réutilise map_accounting pour achats/avoirs ; ventes construites ici."""
        ht = float(vat.amount_ht)
        tva = float(vat.amount_vat)
        ttc = float(vat.amount_ttc)
        supplier = (
            payload.get("supplier_name")
            or (
                payload.get("supplier", {}).get("name")
                if isinstance(payload.get("supplier"), dict)
                else None
            )
            or "Tiers"
        )
        customer = (
            payload.get("customer_name")
            or (
                payload.get("customer", {}).get("name")
                if isinstance(payload.get("customer"), dict)
                else None
            )
            or "Client"
        )
        number = (
            payload.get("document_number")
            or payload.get("invoice_number")
            or "SANS-REF"
        )
        date = payload.get("document_date") or payload.get("invoice_date") or ""

        is_sale = direction == DocumentDirection.SALE.value
        is_credit = (document_type or "").lower() in {"credit_note", "avoir"}

        if not is_sale:
            # Réutiliser mapper historique
            fr_type = "avoir" if is_credit else "facture"
            extraction = ExtractionResult(
                supplier=str(supplier),
                invoice_number=str(number),
                invoice_date=str(date) if date else None,
                amount_ht=ht,
                amount_tva=tva,
                amount_ttc=ttc,
                document_type=fr_type,
            )
            entry = map_accounting(
                extraction,
                expense_account=accounts["expense_or_revenue"],
                vat_account=accounts["vat_account"],
                supplier_account=accounts["third_party"],
            )
            lines = []
            for i, line in enumerate(entry.lines, start=1):
                lines.append(
                    {
                        "line_number": i,
                        "account_code": str(line.account),
                        "account_label": line.label,
                        "debit": float(line.debit or 0),
                        "credit": float(line.credit or 0),
                        "vat_rate": float(vat.vat_rate) if vat.vat_rate is not None else None,
                    }
                )
            # Forcer journal résolu
            return lines, entry.explanation or "mapping_historique"

        # Ventes
        rev = accounts["expense_or_revenue"]
        vat_acc = accounts["vat_account"]
        client = accounts["third_party"]
        if is_credit:
            lines = [
                {
                    "line_number": 1,
                    "account_code": client,
                    "account_label": f"Client {customer}",
                    "debit": 0.0,
                    "credit": ttc,
                },
                {
                    "line_number": 2,
                    "account_code": rev,
                    "account_label": "Ventes",
                    "debit": ht,
                    "credit": 0.0,
                },
                {
                    "line_number": 3,
                    "account_code": vat_acc,
                    "account_label": "TVA collectée",
                    "debit": tva,
                    "credit": 0.0,
                },
            ]
            expl = f"Avoir vente : débit {rev}+{vat_acc}, crédit client {client}"
        else:
            lines = [
                {
                    "line_number": 1,
                    "account_code": client,
                    "account_label": f"Client {customer}",
                    "debit": ttc,
                    "credit": 0.0,
                },
                {
                    "line_number": 2,
                    "account_code": rev,
                    "account_label": "Ventes",
                    "debit": 0.0,
                    "credit": ht,
                },
                {
                    "line_number": 3,
                    "account_code": vat_acc,
                    "account_label": "TVA collectée",
                    "debit": 0.0,
                    "credit": tva,
                },
            ]
            expl = f"Vente : débit client {client}, crédit {rev}+{vat_acc}"
        for ln in lines:
            ln["vat_rate"] = float(vat.vat_rate) if vat.vat_rate is not None else None
        return lines, expl
