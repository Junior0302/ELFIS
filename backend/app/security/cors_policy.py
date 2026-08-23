"""Résolution des origines CORS — développement vs production."""

from __future__ import annotations

DEV_LOCAL_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def is_local_origin(origin: str) -> bool:
    raw = (origin or "").strip().lower()
    if not raw:
        return False
    host = raw.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0]
    return host in {"localhost", "127.0.0.1", "::1"}


def parse_origin_list(raw: str) -> list[str]:
    return [item.strip().rstrip("/") for item in (raw or "").split(",") if item.strip()]


def resolve_cors_allow_origins(
    *,
    cors_origins: str,
    frontend_url: str,
    production: bool,
) -> list[str]:
    """Production : uniquement CORS_ORIGINS + FRONTEND_URL HTTPS. Jamais * ni localhost."""
    configured = parse_origin_list(cors_origins)
    frontend = (frontend_url or "").strip().rstrip("/")

    if not production:
        if not configured or configured == ["*"]:
            return ["*"]
        origins = list(configured)
        origins.extend(DEV_LOCAL_ORIGINS)
        if frontend:
            origins.append(frontend)
        return list(dict.fromkeys(origins))

    origins: list[str] = []
    for origin in configured:
        if origin == "*" or is_local_origin(origin):
            continue
        if origin.startswith("https://"):
            origins.append(origin)
    if frontend.startswith("https://") and not is_local_origin(frontend):
        origins.append(frontend)
    return list(dict.fromkeys(origins))
