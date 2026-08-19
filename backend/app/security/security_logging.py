"""Logging sécurité — délègue à la redaction centrale."""

from __future__ import annotations

from typing import Any

from app.security.security_redaction import safe_log_context


def safe_security_log_context(**fields: Any) -> dict[str, Any]:
    return safe_log_context(**fields)
