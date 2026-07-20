"""Sécurité et confidentialité — AI Engine."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.ai.ai_exceptions import AIValidationError

FORBIDDEN_INPUT_KEYS = frozenset(
    {
        "pdf",
        "pdf_bytes",
        "pdf_base64",
        "file_content",
        "content_base64",
        "jwt",
        "api_key",
        "apikey",
        "password",
        "supabase_key",
        "service_role_key",
        "authorization",
        "signed_url",
        "openai_api_key",
        "token",
        "access_token",
        "refresh_token",
    }
)

_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|authorization|bearer|jwt|openai)[=:\s]+[^\s,;]+"
)
_IBAN_RE = re.compile(r"\b([A-Z]{2}\d{2}[A-Z0-9]{10,30})\b")
_PROMPT_INJECTION_RE = re.compile(
    r"(?i)(ignore\s+(all\s+)?previous|system\s*prompt|you\s+are\s+now|jailbreak)"
)


def sanitize_ai_error(message: str | None, *, max_len: int = 500) -> str | None:
    if message is None:
        return None
    cleaned = _SECRET_RE.sub(r"\1=***", str(message))
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 3] + "..."
    return cleaned


def safe_ai_log_context(
    *,
    execution_id: str | None = None,
    task_name: str | None = None,
    organization_id: int | None = None,
    provider: str | None = None,
    model: str | None = None,
    status: str | None = None,
    latency_ms: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    estimated_cost: float | None = None,
    job_id: str | None = None,
    correlation_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    for key, val in {
        "execution_id": execution_id,
        "task_name": task_name,
        "organization_id": organization_id,
        "provider": provider,
        "model": model,
        "status": status,
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost": estimated_cost,
        "job_id": job_id,
        "correlation_id": correlation_id,
    }.items():
        if val is not None:
            ctx[key] = val
    forbidden = {
        "input_data",
        "result",
        "prompt",
        "payload",
        "pdf",
        "api_key",
        "token",
        "content",
        "extracted_text",
    }
    for k, v in extra.items():
        if k.lower() in forbidden:
            continue
        ctx[k] = v
    return ctx


def assert_safe_ai_input(data: dict[str, Any] | None, *, max_bytes: int) -> dict[str, Any]:
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise AIValidationError("input_data doit être un objet JSON")

    for key in data:
        lk = str(key).lower()
        if lk in FORBIDDEN_INPUT_KEYS or any(
            x in lk for x in ("password", "api_key", "jwt", "secret", "token")
        ):
            raise AIValidationError(f"input_data contient une clé interdite: {key}")

    # Pas de base64 / PDF volumineux dans les valeurs
    for key, value in data.items():
        if isinstance(value, str):
            if value.startswith("%PDF") or value.startswith("JVBERi0"):
                raise AIValidationError(f"contenu PDF interdit dans {key}")
            if len(value) > 120_000 and ("base64" in key.lower() or len(value) > max_bytes):
                raise AIValidationError(f"valeur trop volumineuse: {key}")

    raw = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    if len(raw) > max_bytes:
        raise AIValidationError(f"input_data trop volumineux (max {max_bytes} octets)")

    return data


def sanitize_input_for_llm(data: dict[str, Any]) -> dict[str, Any]:
    """Copie limitée pour envoi LLM — masque IBAN si présent, tronque texte."""
    out: dict[str, Any] = {}
    for key, value in data.items():
        if key in FORBIDDEN_INPUT_KEYS:
            continue
        if key == "extracted_text" and isinstance(value, str):
            text = value[:8000]
            text = _IBAN_RE.sub(lambda m: m.group(1)[:4] + "***", text)
            if _PROMPT_INJECTION_RE.search(text[:500]):
                # Ne bloque pas : on journalise via truncation / ne pas injecter en system
                text = text.replace("ignore previous", "[filtered]")
            out[key] = text
        elif key in ("supplier_iban", "iban") and isinstance(value, str) and value:
            out[key] = value[:4] + "***"
        elif isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
        elif isinstance(value, dict):
            out[key] = sanitize_input_for_llm(value)
        elif isinstance(value, list) and len(value) <= 50:
            out[key] = value[:50]
    return out


def limit_result(result: dict[str, Any] | None, *, max_bytes: int) -> dict[str, Any] | None:
    if result is None:
        return None
    raw = json.dumps(result, ensure_ascii=False, default=str).encode("utf-8")
    if len(raw) <= max_bytes:
        return result
    return {"truncated": True, "message": "result trop volumineux"}


def input_hash(data: dict[str, Any]) -> str:
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
