"""Détection de doublons entre documents extraits — propositions uniquement."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.document_extraction.models import ElfisDocumentExtraction
from app.validation_mapping.enums import DuplicateSeverity


def _norm(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip().lower().replace(" ", "")


def detect_document_duplicates(
    db: Session,
    *,
    organization_id: int,
    current_extraction: ElfisDocumentExtraction,
    validated_data: dict[str, Any],
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Compare avec d'autres extractions de l'org — ne supprime jamais."""
    others = (
        db.query(ElfisDocumentExtraction)
        .filter(ElfisDocumentExtraction.organization_id == organization_id)
        .filter(ElfisDocumentExtraction.id != current_extraction.id)
        .filter(
            ElfisDocumentExtraction.status.in_(
                [
                    "awaiting_human_validation",
                    "completed",
                    "completed_with_warnings",
                ]
            )
        )
        .order_by(ElfisDocumentExtraction.created_at.desc())
        .limit(200)
        .all()
    )
    cur_num = _norm(
        validated_data.get("document_number")
        or validated_data.get("quote_number")
        or validated_data.get("credit_note_number")
    )
    cur_date = _norm(validated_data.get("document_date") or validated_data.get("issue_date"))
    amounts = validated_data.get("amounts") if isinstance(validated_data.get("amounts"), dict) else {}
    cur_total = _norm(amounts.get("total_including_tax"))
    cur_cur = _norm(validated_data.get("currency"))
    supplier = validated_data.get("supplier") if isinstance(validated_data.get("supplier"), dict) else {}
    cur_sup = _norm(supplier.get("name") or supplier.get("legal_name"))
    cur_siren = _norm(supplier.get("registration_number"))
    cur_vat = _norm(supplier.get("vat_number"))
    cur_iban = _norm(supplier.get("iban") or supplier.get("iban_masked"))

    results: list[dict[str, Any]] = []
    for o in others:
        data = o.structured_data or {}
        matched: list[str] = []
        score = 0.0
        o_num = _norm(
            data.get("document_number") or data.get("quote_number") or data.get("credit_note_number")
        )
        o_date = _norm(data.get("document_date") or data.get("issue_date"))
        o_amt = data.get("amounts") if isinstance(data.get("amounts"), dict) else {}
        o_total = _norm(o_amt.get("total_including_tax"))
        o_cur = _norm(data.get("currency"))
        o_sup_obj = data.get("supplier") if isinstance(data.get("supplier"), dict) else {}
        o_sup = _norm(o_sup_obj.get("name") or o_sup_obj.get("legal_name"))
        o_siren = _norm(o_sup_obj.get("registration_number"))
        o_vat = _norm(o_sup_obj.get("vat_number"))
        o_iban = _norm(o_sup_obj.get("iban") or o_sup_obj.get("iban_masked"))

        if cur_num and cur_num == o_num:
            matched.append("document_number")
            score += 0.35
        if cur_date and cur_date == o_date:
            matched.append("document_date")
            score += 0.15
        if cur_total and cur_total == o_total:
            matched.append("total_including_tax")
            score += 0.2
        if cur_cur and cur_cur == o_cur:
            matched.append("currency")
            score += 0.05
        if cur_sup and cur_sup == o_sup:
            matched.append("supplier.name")
            score += 0.15
        if cur_siren and cur_siren == o_siren and len(cur_siren) >= 9:
            matched.append("siren")
            score += 0.25
        if cur_vat and cur_vat == o_vat:
            matched.append("vat_number")
            score += 0.2
        if cur_iban and cur_iban == o_iban and len(cur_iban) > 8:
            matched.append("iban")
            score += 0.2

        if score < 0.35 or not matched:
            continue
        severity = (
            DuplicateSeverity.EXACT.value
            if score >= 0.85 and "document_number" in matched
            else DuplicateSeverity.PROBABLE.value
            if score >= 0.55
            else DuplicateSeverity.WEAK.value
        )
        results.append(
            {
                "other_document_id": o.document_intake_item_id,
                "other_universal_document_id": o.universal_document_id,
                "other_extraction_id": o.id,
                "severity": severity,
                "score": round(min(1.0, score), 3),
                "matched_fields": matched,
                "explanation": f"Correspondance sur {', '.join(matched)}",
            }
        )
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
