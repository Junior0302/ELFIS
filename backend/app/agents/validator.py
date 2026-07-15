from __future__ import annotations

from app.schemas import ExtractionResult, ValidationResult

REQUIRED = [
    ("supplier", "fournisseur"),
    ("invoice_date", "date"),
    ("invoice_number", "numéro"),
    ("amount_ht", "montant HT"),
    ("amount_tva", "montant TVA"),
    ("amount_ttc", "montant TTC"),
    ("vat_rate", "taux de TVA"),
]


def validate_financials(
    extraction: ExtractionResult,
    confidence_threshold: float = 0.85,
    default_vat_rate: float = 20.0,
) -> ValidationResult:
    anomalies: list[str] = []
    missing: list[str] = []

    for attr, label in REQUIRED:
        if getattr(extraction, attr) in (None, ""):
            missing.append(label)

    ht = extraction.amount_ht
    tva = extraction.amount_tva
    ttc = extraction.amount_ttc
    rate = extraction.vat_rate

    if ht is not None and tva is not None and ttc is not None:
        expected = round(ht + tva, 2)
        if abs(expected - round(ttc, 2)) > 0.05:
            anomalies.append(
                f"Incohérence HT + TVA ≠ TTC (attendu {expected:.2f}, relevé {ttc:.2f})"
            )

    if ht is not None and rate is not None and tva is not None and ht != 0:
        expected_tva = round(ht * (rate / 100.0), 2)
        if abs(expected_tva - round(tva, 2)) > 0.05:
            anomalies.append(
                f"TVA incohérente avec le taux {rate}% (attendu {expected_tva:.2f}, relevé {tva:.2f})"
            )

    if rate is not None and rate not in (0.0, 5.5, 10.0, 20.0):
        # tolérance légère pour 5.5 vs 5.50
        if rate not in (5.5, 10.0, 20.0) and abs(rate - default_vat_rate) > 0.2:
            anomalies.append(f"Taux de TVA inhabituel: {rate}%")

    if extraction.confidence_score < confidence_threshold:
        anomalies.append(
            f"Score de confiance faible ({extraction.confidence_score:.0%} < {confidence_threshold:.0%})"
        )

    needs_review = bool(anomalies or missing or extraction.confidence_score < confidence_threshold)
    return ValidationResult(
        is_valid=not anomalies and not missing,
        needs_review=needs_review,
        anomalies=anomalies,
        missing_fields=missing,
        corrected=extraction,
    )