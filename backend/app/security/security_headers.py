"""En-têtes HTTP de sécurité."""

from __future__ import annotations

from starlette.responses import Response

from app.security.security_config import is_production, snapshot

# CSP compatible Stripe Checkout + Vite/React (report-only par défaut).
DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com https://www.gstatic.com https://www.googleapis.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob: https:; "
    "connect-src 'self' https: http://localhost:* http://127.0.0.1:* "
    "https://api.stripe.com https://*.googleapis.com https://*.firebaseio.com https://identitytoolkit.googleapis.com; "
    "frame-src https://js.stripe.com https://hooks.stripe.com https://*.firebaseapp.com; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self' https://checkout.stripe.com; "
    "frame-ancestors 'none'"
)


def apply_security_headers(response: Response, *, path: str = "") -> None:
    cfg = snapshot()
    if not cfg.security_headers_enabled:
        return

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(self), geolocation=(), payment=()",
    )
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "cross-origin")

    if cfg.csp_enabled:
        header_name = (
            "Content-Security-Policy-Report-Only"
            if cfg.csp_report_only
            else "Content-Security-Policy"
        )
        response.headers.setdefault(header_name, DEFAULT_CSP)

    if "server" in response.headers:
        del response.headers["server"]

    if path.startswith("/api/") and "Cache-Control" not in response.headers:
        response.headers["Cache-Control"] = "no-store"

    # HSTS uniquement prod + flag explicite (évite local HTTP).
    if cfg.hsts_enabled and is_production():
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
