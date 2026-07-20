"""Tâche document.classify.v1."""

from __future__ import annotations

from typing import Any

from app.ai.ai_context import AIContext
from app.ai.ai_exceptions import AIValidationError
from app.ai.ai_registry import AITask
from app.ai.ai_security import sanitize_input_for_llm
from app.ai.ai_types import AITaskNames, CLASSIFICATION_TYPES, READER_TYPE_TO_AI
from app.ai.providers.base import AIProvider
from app.services.ocr import detect_document_type


class DocumentClassifyTask(AITask):
    task_name = AITaskNames.DOCUMENT_CLASSIFY
    task_version = 1
    default_provider = "openai"
    prompt_version = "classify-v1"

    def execute(
        self,
        input_data: dict[str, Any],
        context: AIContext,
        provider: AIProvider | None,
    ) -> dict[str, Any]:
        text = str(input_data.get("extracted_text") or "").strip()
        filename = str(input_data.get("filename") or "document.pdf")
        if not text:
            return {
                "document_type": "other",
                "confidence": 0.0,
                "possible_types": [{"type": "other", "confidence": 0.0}],
                "requires_review": True,
                "reason": "extracted_text_unavailable",
                "blocked": True,
            }

        safe = sanitize_input_for_llm({"extracted_text": text, "filename": filename})

        if provider is not None:
            try:
                resp = provider.execute_structured(
                    model=context.model,
                    system=(
                        "Tu classifies des documents comptables français. "
                        "JSON strict uniquement. Types autorisés: "
                        + ", ".join(sorted(CLASSIFICATION_TYPES))
                    ),
                    user=(
                        f"Fichier: {safe.get('filename')}\n"
                        f"Texte:\n{safe.get('extracted_text')}\n"
                        "Retourne: document_type, confidence (0-1), "
                        "possible_types (liste {type,confidence}), requires_review, reason."
                    ),
                )
                data = resp.structured_output or {}
                return self._normalize(data, provider_meta=resp)
            except Exception:
                pass

        # Fallback déterministe — détecteur OCR existant
        reader_type = detect_document_type(text, filename)
        ai_type = READER_TYPE_TO_AI.get(reader_type, "other")
        conf = 0.55 if text and len(text) > 80 else 0.35
        return {
            "document_type": ai_type,
            "confidence": conf,
            "possible_types": [{"type": ai_type, "confidence": conf}],
            "requires_review": conf < 0.7,
            "reason": "heuristic_detect_document_type",
            "_usage": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        }

    def validate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        result = super().validate_output(result)
        doc_type = str(result.get("document_type") or "").strip()
        if doc_type not in CLASSIFICATION_TYPES:
            raise AIValidationError(f"document_type invalide: {doc_type}")
        conf = float(result.get("confidence") or 0)
        if conf < 0 or conf > 1:
            raise AIValidationError("confidence hors intervalle")
        requires = bool(result.get("requires_review")) or conf < 0.7 or bool(result.get("blocked"))
        result["requires_review"] = requires
        result["confidence"] = conf
        possibles = result.get("possible_types") or []
        if not isinstance(possibles, list):
            raise AIValidationError("possible_types invalide")
        cleaned = []
        for item in possibles[:10]:
            if not isinstance(item, dict):
                continue
            t = str(item.get("type") or "")
            if t not in CLASSIFICATION_TYPES:
                continue
            cleaned.append({"type": t, "confidence": float(item.get("confidence") or 0)})
        result["possible_types"] = cleaned or [{"type": doc_type, "confidence": conf}]
        result["reason"] = str(result.get("reason") or "")[:500]
        return result

    def _normalize(self, data: dict[str, Any], *, provider_meta) -> dict[str, Any]:
        doc_type = str(data.get("document_type") or "other")
        if doc_type not in CLASSIFICATION_TYPES:
            doc_type = "other"
        conf = float(data.get("confidence") or 0.5)
        out = {
            "document_type": doc_type,
            "confidence": conf,
            "possible_types": data.get("possible_types")
            or [{"type": doc_type, "confidence": conf}],
            "requires_review": bool(data.get("requires_review")) or conf < 0.7,
            "reason": str(data.get("reason") or "llm_classification")[:500],
            "_usage": {
                "input_tokens": provider_meta.input_tokens,
                "output_tokens": provider_meta.output_tokens,
                "total_tokens": provider_meta.total_tokens,
                "latency_ms": provider_meta.latency_ms,
            },
        }
        return out
