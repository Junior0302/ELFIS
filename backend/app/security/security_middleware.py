"""Middleware sécurité consolidé — request ID, rate limit, headers, payload."""

from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.observability.metrics import metrics_registry
from app.observability.request_context import (
    bind_request_ids,
    clear_request_context,
    get_correlation_id,
    get_request_id,
    normalize_id_header,
    normalize_optional_id,
)
from app.security.security_config import snapshot
from app.security.security_exceptions import SecurityError, error_response
from app.security.security_headers import apply_security_headers
from app.security.security_payload_limits import check_content_length, max_bytes_for_path
from app.security.security_rate_limit import (
    RateLimitCategory,
    category_for_path,
    check_rate_limit,
)
from app.security.security_types import ErrorCode

logger = logging.getLogger("elfis.security.middleware")


def _client_ip(request: Request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded[:64]
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class SecurityMiddleware(BaseHTTPMiddleware):
    """Garde-fous HTTP consolidés (remplace / étend SecurityHeadersMiddleware)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        started = time.perf_counter()
        path = request.url.path
        method = request.method.upper()

        request_id = normalize_id_header(request.headers.get("x-request-id"))
        correlation_id = normalize_optional_id(request.headers.get("x-correlation-id")) or request_id
        bind_request_ids(request_id=request_id, correlation_id=correlation_id)
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        try:
            if method not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}:
                return self._err(
                    405,
                    ErrorCode.METHOD_NOT_ALLOWED,
                    "Méthode non autorisée",
                    request_id,
                    correlation_id,
                )

            try:
                check_content_length(
                    request.headers.get("content-length"),
                    max_bytes=max_bytes_for_path(path),
                )
            except SecurityError as exc:
                return self._err(
                    exc.status_code,
                    exc.code,
                    exc.message,
                    request_id,
                    correlation_id,
                    details=exc.details,
                )

            cfg = snapshot()
            if cfg.rate_limit_enabled and method != "OPTIONS":
                cat = category_for_path(path)
                # Webhooks : limite large, clé sans IP seule (évite de bloquer retries Stripe)
                if cat == RateLimitCategory.WEBHOOK:
                    result = check_rate_limit(
                        RateLimitCategory.WEBHOOK,
                        route=path,
                    )
                elif cat is not None:
                    result = check_rate_limit(
                        cat,
                        ip=_client_ip(request),
                        route=path,
                    )
                else:
                    result = None

                if result is not None and not result.allowed:
                    metrics_registry.incr("http_rate_limit_hits", labels={"category": result.category})
                    return self._err(
                        429,
                        ErrorCode.RATE_LIMIT_EXCEEDED,
                        "Trop de requêtes. Réessayez plus tard.",
                        request_id,
                        correlation_id,
                        details={"category": result.category, "limit": result.limit},
                        headers={"Retry-After": str(result.retry_after_seconds)},
                    )

            response = await call_next(request)
        except Exception:
            clear_request_context()
            raise

        # Headers IDs + sécurité
        response.headers["X-Request-Id"] = get_request_id() or request_id
        response.headers["X-Correlation-Id"] = get_correlation_id() or correlation_id
        apply_security_headers(response, path=path)

        duration_ms = (time.perf_counter() - started) * 1000
        metrics_registry.incr("http_requests_total", labels={"method": method, "status": str(response.status_code)})
        metrics_registry.observe("http_request_duration_ms", duration_ms, labels={"route": path[:80]})
        if response.status_code >= 500:
            metrics_registry.incr("http_errors_total", labels={"status": str(response.status_code)})

        clear_request_context()
        return response

    def _err(
        self,
        status: int,
        code: str,
        message: str,
        request_id: str,
        correlation_id: str,
        *,
        details: dict | None = None,
        headers: dict[str, str] | None = None,
    ):
        hdrs = {
            "X-Request-Id": request_id,
            "X-Correlation-Id": correlation_id,
            **(headers or {}),
        }
        resp = error_response(
            status_code=status,
            code=code,
            message=message,
            request_id=request_id,
            correlation_id=correlation_id,
            details=details,
            headers=hdrs,
            legacy_detail={"code": code, "message": message, **(details or {})},
        )
        apply_security_headers(resp, path="/api/")
        clear_request_context()
        return resp


# Alias rétrocompat
SecurityHeadersMiddleware = SecurityMiddleware
