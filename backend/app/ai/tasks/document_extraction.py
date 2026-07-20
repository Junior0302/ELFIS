"""Tâche document.extract_invoice.v1 — réutilise Document Reader."""

from __future__ import annotations

from typing import Any

from app.agents.reader import _heuristic_extraction, _structured_extract
from app.ai.ai_context import AIContext
from app.ai.ai_exceptions import AIValidationError
from app.ai.ai_registry import AITask
from app.ai.ai_security import sanitize_input_for_llm
from app.ai.ai_types import AITaskNames
from app.ai.providers.base import AIProvider
from app.config import settings
from app.schemas import ExtractionResult


class DocumentExtractInvoiceTask(AITask):
    task_name = AITaskNames.DOCUMENT_EXTRACT_INVOICE
    task_version = 1
    default_provider = "openai"
    prompt_version = "extract-invoice-v1"

    def execute(
        self,
        input_data: dict[str, Any],
        context: AIContext,
        provider: AIProvider | None,
    ) -> dict[str, Any]:
        text = str(input_data.get("extracted_text") or "").strip()
        filename = str(input_data.get("filename") or "invoice.pdf")
        if not text:
            return {
                "supplier": None,
                "customer": None,
                "invoice": None,
                "amounts": None,
                "legal": None,
                "confidence": 0.0,
                "needs_review": True,
                "blocked": True,
                "reason": "extracted_text_unavailable",
            }

        safe = sanitize_input_for_llm({"extracted_text": text, "filename": filename})
        text_s = str(safe.get("extracted_text") or "")
        usage = {"input_tokens": None, "output_tokens": None, "total_tokens": None}

        extraction: ExtractionResult
        if provider is not None and settings.openai_api_key:
            # Réutilise le prompt Document Reader existant via _structured_extract
            # (même schéma ExtractionResult) — le provider est injecté pour les tests mock.
            try:
                # Si provider mocké expose execute_structured, on mappe manuellement
                if hasattr(provider, "execute_structured") and type(provider).__name__ != "OpenAIProvider":
                    resp = provider.execute_structured(
                        model=context.model,
                        system="Tu extrais des factures. JSON strict compatible ExtractionResult.",
                        user=f"Fichier: {filename}\nTexte:\n{text_s[:8000]}",
                    )
                    data = resp.structured_output or {}
                    extraction = ExtractionResult.model_validate(
                        {
                            **data,
                            "raw_text": data.get("raw_text") or text_s[:2000],
                            "document_type": data.get("document_type") or "facture",
                            "confidence_score": data.get("confidence_score")
                            or data.get("confidence")
                            or 0.7,
                        }
                    )
                    usage = {
                        "input_tokens": resp.input_tokens,
                        "output_tokens": resp.output_tokens,
                        "total_tokens": resp.total_tokens,
                        "latency_ms": resp.latency_ms,
                    }
                else:
                    extraction = _structured_extract(text_s, filename)
            except Exception:
                extraction = _heuristic_extraction(filename, text_s, "text")
        else:
            extraction = _heuristic_extraction(filename, text_s, "text")

        return self._to_output(extraction, usage=usage)

    def validate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        result = super().validate_output(result)
        for key in ("supplier", "customer", "invoice", "amounts", "legal"):
            if key not in result:
                raise AIValidationError(f"clé manquante: {key}")
        conf = float(result.get("confidence") or 0)
        if conf < 0 or conf > 1:
            raise AIValidationError("confidence hors intervalle")
        result["needs_review"] = bool(result.get("needs_review")) or conf < 0.7
        return result

    def _to_output(self, extraction: ExtractionResult, *, usage: dict) -> dict[str, Any]:
        return {
            "supplier": {
                "name": extraction.supplier,
                "address": extraction.supplier_address,
                "siret": extraction.supplier_siret,
                "vat": extraction.supplier_vat,
                "email": extraction.supplier_email,
                "iban_masked": (extraction.supplier_iban[:4] + "***")
                if extraction.supplier_iban
                else None,
            },
            "customer": {
                "name": extraction.customer_name,
                "address": extraction.customer_address,
                "siret": extraction.customer_siret,
                "vat": extraction.customer_vat,
            },
            "invoice": {
                "number": extraction.invoice_number,
                "date": extraction.invoice_date,
                "due_date": extraction.due_date,
                "document_type": extraction.document_type,
                "currency": extraction.currency,
                "order_reference": extraction.order_reference,
            },
            "amounts": {
                "amount_ht": extraction.amount_ht,
                "amount_tva": extraction.amount_tva,
                "amount_ttc": extraction.amount_ttc,
                "vat_rate": extraction.vat_rate,
            },
            "legal": {
                "late_penalty_mention": extraction.late_penalty_mention,
                "recovery_indemnity_mention": extraction.recovery_indemnity_mention,
                "vat_exemption_mention": extraction.vat_exemption_mention,
                "reverse_charge_mention": extraction.reverse_charge_mention,
            },
            "confidence": float(extraction.confidence_score or 0),
            "needs_review": float(extraction.confidence_score or 0) < 0.7,
            "compatible_extraction": extraction.model_dump(mode="json"),
            "_usage": usage,
        }
