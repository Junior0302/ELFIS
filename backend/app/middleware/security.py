"""Compat — délègue au middleware Security V1."""

from __future__ import annotations

from app.security.security_middleware import SecurityHeadersMiddleware, SecurityMiddleware

__all__ = ["SecurityHeadersMiddleware", "SecurityMiddleware"]
