"""Tâche document.quality_check.v1 — déterministe (Invoice Validator)."""

from __future__ import annotations

from typing import Any

from app.agents.validator import validate_financials
from app.ai.ai_context import AIContext
from app.ai.ai_exceptions import AIValidationError
from app.ai.ai_registry import AITask
from app.ai.ai_types import AITaskNames
from app.ai.providers.base import AIProvider
from app.schemas import ExtractionResult


class DocumentQualityCheckTask(AITask):
    """Orchestration de contrôles non-LLM (Quality / Invoice / Financial validators)."""

    task_name = AITaskNames.DOCUMENT_QUALITY_CHECK
    task_version = 1
    default_provider = "openai"  # non utilisé pour V1 déterministe
    prompt_version = "quality-v1"

    def execute(
        self,
        input_data: dict[str, Any],
        context: AIContext,
        provider: AIProvider | None,
    ) -> dict[str, Any]:
        # provider volontairement ignoré — contrôles déterministes
        _ = provider
        extraction_raw = input_data.get("extraction") or input_data.get("compatible_extraction")
        if isinstance(extraction_raw, dict):
            try:
                extraction = ExtractionResult.model_validate(extraction_raw)
            except Exception as exc:
                raise AIValidationError(f"extraction invalide: {exc}") from exc
        else:
            # Reconstruire depuis amounts/invoice si fournis
            amounts = input_data.get("amounts") or {}
            invoice = input_data.get("invoice") or {}
            supplier = input_data.get("supplier") or {}
            if not amounts and not invoice:
                text = str(input_data.get("extracted_text") or "").strip()
                if not text:
                    return {
                        "status": "invalid",
                        "confidence": 0.0,
                        "missing_fields": ["extraction"],
                        "errors": ["extracted_text_unavailable"],
                        "warnings": [],
                        "financial_checks": {},
                        "requires_review": True,
                        "blocked": True,
                    }
                from app.agents.reader import _heuristic_extraction

                extraction = _heuristic_extraction(
                    str(input_data.get("filename") or "doc.pdf"), text, "text"
                )
            else:
                extraction = ExtractionResult(
                    supplier=(supplier.get("name") if isinstance(supplier, dict) else None),
                    invoice_date=invoice.get("date"),
                    invoice_number=invoice.get("number"),
                    amount_ht=amounts.get("amount_ht"),
                    amount_tva=amounts.get("amount_tva"),
                    amount_ttc=amounts.get("amount_ttc"),
                    vat_rate=amounts.get("vat_rate"),
                    document_type=invoice.get("document_type") or "facture",
                    confidence_score=float(input_data.get("confidence") or 0.7),
                )

        validation = validate_financials(extraction)
        financial_checks = {
            "ht_plus_tva_equals_ttc": not any(
                "HT + TVA" in a or "HT + TVA" in a for a in validation.anomalies
            )
            and not any("≠ TTC" in a for a in validation.anomalies),
            "vat_rate_consistent": not any("TVA incohérente" in a for a in validation.anomalies),
            "is_valid": validation.is_valid,
        }
        # Corriger ht_plus check properly
        financial_checks["ht_plus_tva_equals_ttc"] = not any(
            "≠ TTC" in a for a in validation.anomalies
        )

        if validation.is_valid and not validation.needs_review:
            status = "valid"
        elif validation.anomalies and not validation.missing_fields:
            status = "warning"
        else:
            status = "invalid" if (validation.anomalies or validation.missing_fields) else "warning"

        conf = float(extraction.confidence_score or 0)
        if validation.anomalies:
            conf = min(conf, 0.6)

        return {
            "status": status,
            "confidence": conf,
            "missing_fields": list(validation.missing_fields),
            "errors": [a for a in validation.anomalies if "confiance" not in a.lower()],
            "warnings": [a for a in validation.anomalies if "confiance" in a.lower()],
            "financial_checks": financial_checks,
            "requires_review": bool(validation.needs_review),
            "_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        }

    def validate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        result = super().validate_output(result)
        if result.get("status") not in ("valid", "warning", "invalid"):
            raise AIValidationError("status quality invalide")
        return result
