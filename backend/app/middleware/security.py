from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

# Fenêtre glissante simple (par process) — anti-bruteforce basique.
_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_RATE_LOCK = Lock()

SENSITIVE_PREFIXES = (
    "/api/auth/firebase-session",
    "/api/auth/login",
    "/api/auth/register",
    "/api/subscriptions/checkout",
    "/api/subscriptions/portal",
)


def _client_ip(request: Request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded[:64]
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _rate_limited(key: str, *, limit: int, window_s: float) -> bool:
    now = time.monotonic()
    with _RATE_LOCK:
        bucket = _RATE_BUCKETS[key]
        while bucket and now - bucket[0] > window_s:
            bucket.popleft()
        if len(bucket) >= limit:
            return True
        bucket.append(now)
        return False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """7 garde-fous applicatifs exposés côté HTTP."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1) Bloquer méthodes exotiques
        if request.method.upper() not in {
            "GET",
            "HEAD",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS",
        }:
            return JSONResponse({"detail": "Méthode non autorisée"}, status_code=405)

        # 2) Limiter la taille annoncée (DoS basique)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > 12 * 1024 * 1024:
                    return JSONResponse({"detail": "Requête trop volumineuse"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "En-tête invalide"}, status_code=400)

        # 3) Rate-limit sur endpoints sensibles
        path = request.url.path
        if any(path.startswith(prefix) for prefix in SENSITIVE_PREFIXES):
            ip = _client_ip(request)
            if _rate_limited(f"{ip}:{path}", limit=30, window_s=60.0):
                logger.warning("Rate limit hit ip=%s path=%s", ip, path)
                return JSONResponse(
                    {"detail": {"code": "rate_limited", "message": "Trop de tentatives. Réessayez plus tard."}},
                    status_code=429,
                )

        # 4) Pas de cache sur réponses API authentifiées
        response = await call_next(request)

        # 5) En-têtes de durcissement navigateur / reverse-proxy
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(self), geolocation=(), payment=()",
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "cross-origin")

        # 6) Pas de fuite serveur
        if "server" in response.headers:
            del response.headers["server"]

        # 7) Cache-Control strict hors assets publics
        if path.startswith("/api/") and "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store"

        if settings.app_env.lower() == "production":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response
