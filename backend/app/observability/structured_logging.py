"""Logs structurés JSON / texte."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.observability.request_context import current_context
from app.security.security_redaction import redact_mapping, safe_log_context


class StructuredLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ctx = current_context()
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "service": "elfis-core",
            "environment": getattr(settings, "elfis_environment", None) or settings.app_env,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": ctx.get("request_id"),
            "correlation_id": ctx.get("correlation_id"),
            "organization_id": ctx.get("organization_id"),
            "user_id": ctx.get("user_id"),
        }
        extra = getattr(record, "elfis", None)
        if isinstance(extra, dict):
            payload.update(redact_mapping(extra))
        if record.exc_info and settings.app_env.lower() != "production":
            payload["exc_info"] = self.formatException(record.exc_info)[:2000]
        fmt = (getattr(settings, "elfis_log_format", "json") or "json").lower()
        if fmt == "text":
            return (
                f"{payload['timestamp']} {payload['level']} "
                f"req={payload.get('request_id')} {payload['message']}"
            )
        return json.dumps(payload, ensure_ascii=False, default=str)


_configured = False


def configure_structured_logging() -> None:
    global _configured
    if _configured:
        return
    level_name = (getattr(settings, "elfis_log_level", "INFO") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredLogFormatter())
    # Remplacer handlers basiques uniquement si aucun custom
    if not root.handlers:
        root.addHandler(handler)
    else:
        for h in root.handlers:
            h.setFormatter(StructuredLogFormatter())
    _configured = True


def log_event(logger: logging.Logger, level: int, event_type: str, **fields: Any) -> None:
    include_body = bool(getattr(settings, "elfis_log_include_request_body", False))
    if not include_body:
        fields.pop("body", None)
        fields.pop("request_body", None)
        fields.pop("response_body", None)
        fields.pop("prompt", None)
        fields.pop("raw_text", None)
    logger.log(level, event_type, extra={"elfis": safe_log_context(event_type=event_type, **fields)})
