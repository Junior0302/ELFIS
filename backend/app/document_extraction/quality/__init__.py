"""Réconciliation multi-extracteurs + confiance + cohérence."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from app.config import settings
from app.document_extraction import AMOUNT_TOLERANCE


def reconcile_fields(
    sources: list[tuple[str, dict[str, Any], dict[str, Any]]]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """sources: list of (name, data, provenance)."""
    merged: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    reconciliation: dict[str, Any] = {}

    # flatten all candidate values by path
    candidates: dict[str, list[dict[str, Any]]] = {}
    for name, data, prov in sources:
        flat = _flatten(data)
        for path, value in flat.items():
            if value is None or value == "" or value == []:
                continue
            conf = 0.7
            if path in prov and isinstance(prov[path], dict):
                conf = float(prov[path].get("confidence") or conf)
            candidates.setdefault(path, []).append(
                {"value": value, "source": name, "confidence": conf}
            )

    for path, alts in candidates.items():
        # compare normalized string forms
        groups: dict[str, list] = {}
        for a in alts:
            key = str(a["value"]).strip().lower()
            groups.setdefault(key, []).append(a)
        best_group = max(groups.values(), key=lambda g: (len(g), max(x["confidence"] for x in g)))
        selected = max(best_group, key=lambda x: x["confidence"])
        status = "confirmed" if len(best_group) > 1 else "selected"
        if len(groups) > 1:
            status = "conflicted"
        reconciliation[path] = {
            "selected_value": selected["value"],
            "alternatives": alts,
            "reconciliation_status": status,
            "reason": "MULTIPLE_SOURCES_AGREE"
            if status == "confirmed"
            else ("CONFLICT" if status == "conflicted" else "SINGLE_SOURCE"),
        }
        _set_path(merged, path, selected["value"])
        provenance[path] = {
            "field_path": path,
            "value": selected["value"],
            "raw_value": selected["value"],
            "source": selected["source"],
            "page_number": None,
            "bounding_box": None,
            "extractor_name": selected["source"],
            "extractor_version": "1.0",
            "confidence": selected["confidence"],
            "warnings": ["conflict"] if status == "conflicted" else [],
        }

    return merged, provenance, reconciliation


def compute_field_confidence(provenance: dict[str, Any], quality_score: int | None) -> dict[str, Any]:
    out = {}
    q = (quality_score or 50) / 100.0
    for path, prov in provenance.items():
        base = float(prov.get("confidence") or 0.5)
        source = prov.get("source")
        # Ne jamais faire confiance uniquement au score auto-déclaré LLM
        if source == "llm":
            base = min(base, 0.82)
        # combine quality lightly
        score = max(0.0, min(1.0, base * 0.85 + q * 0.15))
        if source == "heuristic" and base < 0.6:
            score = min(score, 0.65)
        if source == "structured_file":
            score = max(score, min(0.95, base))
        if prov.get("warnings"):
            score = min(score, 0.75)
        # Interdit user_corrected avant Sprint 5
        if source == "user_corrected":
            score = min(score, 0.5)
            prov = {**prov, "warnings": list(prov.get("warnings") or []) + ["user_corrected_forbidden_s4"]}
        level = (
            "high"
            if score >= 0.90
            else "medium"
            if score >= 0.70
            else "low"
            if score >= 0.40
            else "unreliable"
        )
        out[path] = {**prov, "confidence": round(score, 3), "confidence_level": level}
    return out


def compute_global_confidence(
    *,
    field_confidence: dict[str, Any],
    critical_fields: list[str],
    consistency_score: float,
    completeness_score: float,
) -> dict[str, Any]:
    crit_scores = [
        float(field_confidence[f]["confidence"])
        for f in critical_fields
        if f in field_confidence
    ]
    critical = sum(crit_scores) / len(crit_scores) if crit_scores else 0.4
    all_scores = [float(v["confidence"]) for v in field_confidence.values()]
    avg = sum(all_scores) / len(all_scores) if all_scores else 0.3
    overall = 0.45 * critical + 0.25 * avg + 0.15 * consistency_score + 0.15 * completeness_score
    overall = max(0.0, min(1.0, overall))
    level = (
        "high"
        if overall >= 0.90
        else "medium"
        if overall >= 0.70
        else "low"
        if overall >= 0.40
        else "unreliable"
    )
    return {
        "overall_confidence": round(overall, 3),
        "confidence_level": level,
        "critical_fields_confidence": round(critical, 3),
        "completeness_score": round(completeness_score, 3),
        "consistency_score": round(consistency_score, 3),
        "requires_human_review": True,  # toujours pour Migration Center
    }


def check_consistency(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    infos: list[str] = []
    tol = Decimal(str(getattr(settings, "document_validation_amount_tolerance", None) or AMOUNT_TOLERANCE))

    amounts = data.get("amounts") or {}
    if isinstance(amounts, dict):
        try:
            sub = _dec(amounts.get("subtotal_excluding_tax"))
            tax = _dec(amounts.get("total_tax"))
            total = _dec(amounts.get("total_including_tax"))
            shipping = _dec(amounts.get("shipping_amount"))
            discount = _dec(amounts.get("discount_amount"))
            if sub is not None and tax is not None and total is not None:
                expected = sub + tax
                if shipping is not None:
                    expected = expected + shipping
                if discount is not None:
                    expected = expected - discount
                delta = abs(expected - total)
                if delta > tol:
                    errors.append("AMOUNT_MISMATCH_SUBTOTAL_TAX_TOTAL")
                elif delta > Decimal("0"):
                    warnings.append("AMOUNT_WITHIN_TOLERANCE")
                    infos.append("amount_ok")
                else:
                    infos.append("amount_ok")
        except Exception:
            warnings.append("amount_check_skipped")

        # Somme des taxes
        taxes = data.get("taxes")
        if isinstance(taxes, list) and taxes and amounts.get("total_tax") is not None:
            try:
                tax_sum = sum((_dec(t.get("tax_amount")) or Decimal("0")) for t in taxes if isinstance(t, dict))
                total_tax = _dec(amounts.get("total_tax"))
                if total_tax is not None and abs(tax_sum - total_tax) > tol:
                    errors.append("TAX_SUM_MISMATCH")
            except Exception:
                warnings.append("tax_sum_check_skipped")

        # Somme des lignes ≈ subtotal
        lines = data.get("line_items")
        if isinstance(lines, list) and lines and amounts.get("subtotal_excluding_tax") is not None:
            try:
                line_sum = Decimal("0")
                for li in lines:
                    if not isinstance(li, dict):
                        continue
                    lv = _dec(li.get("total_excluding_tax"))
                    if lv is not None:
                        line_sum += lv
                sub = _dec(amounts.get("subtotal_excluding_tax"))
                if sub is not None and line_sum > 0 and abs(line_sum - sub) > tol:
                    errors.append("LINE_ITEMS_SUM_MISMATCH")
            except Exception:
                warnings.append("line_sum_check_skipped")

    # dates
    doc_date = data.get("document_date")
    due = data.get("due_date")
    if doc_date and due and str(due) < str(doc_date):
        errors.append("DUE_DATE_BEFORE_DOCUMENT_DATE")

    iban = None
    supplier = data.get("supplier")
    if isinstance(supplier, dict):
        iban = supplier.get("iban")
    if iban and not _iban_plausible(str(iban)):
        warnings.append("IBAN_STRUCTURE_SUSPECT")

    score = Decimal("1.0")
    score -= Decimal("0.25") * len(errors)
    score -= Decimal("0.08") * len(warnings)
    score = max(Decimal("0"), min(Decimal("1"), score))
    return {
        "errors": errors,
        "warnings": warnings,
        "infos": infos,
        "consistency_score": float(score),
        "tolerance": str(tol),
    }


def _dec(v: Any) -> Decimal | None:
    if v is None or v == "":
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, float):
        # Convertir via str pour éviter artefacts float
        return Decimal(str(v))
    try:
        return Decimal(str(v).replace(",", ".").replace(" ", ""))
    except Exception:
        return None


def completeness(data: dict[str, Any], critical: list[str], recommended: list[str]) -> float:
    flat = _flatten(data)
    if not critical and not recommended:
        return 0.6 if flat else 0.2
    c_ok = sum(1 for f in critical if flat.get(f) not in (None, "", []))
    r_ok = sum(1 for f in recommended if flat.get(f) not in (None, "", []))
    c_score = c_ok / len(critical) if critical else 1.0
    r_score = r_ok / len(recommended) if recommended else 1.0
    return round(0.7 * c_score + 0.3 * r_score, 3)


def _iban_plausible(iban: str) -> bool:
    s = re.sub(r"\s+", "", iban.upper())
    return bool(re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$", s))


def _flatten(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict) and k not in ("line_items", "transactions", "taxes"):
            out.update(_flatten(v, path))
        else:
            out[path] = v
    return out


def _set_path(d: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cur = d
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
        if not isinstance(cur, dict):
            return
    cur[parts[-1]] = value
