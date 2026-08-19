"""Garde-fous RC1 — URL, environnement, masquage credentials."""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse, urlunparse


RECETTE_MARKERS = ("test", "staging", "stage", "recette", "ci", "rc1", "functional")
PROD_MARKERS = ("production", "/prod", "prod.", "live.", "elfis-core.com")
PROD_HOST_FRAGMENTS = ("render.com", "neon.tech", "supabase.co", "supabase.com", "amazonaws.com")


def mask_database_url(url: str) -> str:
    """Masque userinfo (mot de passe) — jamais loguer le secret."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        if parsed.password is None and "@" not in (parsed.netloc or ""):
            return url
        user = parsed.username or ""
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        auth = f"{user}:***" if user else "***"
        netloc = f"{auth}@{host}{port}"
        return urlunparse(
            (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
        )
    except Exception:
        return re.sub(r":([^:@/]+)@", ":***@", url)


def normalize_postgres_url(url: str) -> str:
    """Force le driver psycopg v3 si l’URL n’indique pas de dialecte SQLAlchemy."""
    raw = (url or "").strip()
    if raw.startswith("postgresql+psycopg://") or raw.startswith("postgresql+psycopg2://"):
        return raw
    if raw.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw[len("postgresql://") :]
    if raw.startswith("postgres://"):
        return "postgresql+psycopg://" + raw[len("postgres://") :]
    return raw


def database_name_from_url(url: str) -> str:
    try:
        path = urlparse(url).path or ""
        return path.lstrip("/").split("?")[0].lower()
    except Exception:
        return ""


def assert_safe_rc1_environment(*, environment: str | None = None) -> str:
    env = (environment or os.getenv("ELFIS_ENVIRONMENT") or os.getenv("APP_ENV") or "").strip().lower()
    if env not in {"test", "testing", "staging", "stage"}:
        raise RuntimeError(
            f"RC1 refuse ELFIS_ENVIRONMENT={env!r} — autorisé: test|staging"
        )
    return env


def assert_postgres_tests_enabled() -> None:
    if os.getenv("ELFIS_POSTGRES_TESTS_ENABLED", "").lower() not in {"1", "true", "yes"}:
        raise RuntimeError("ELFIS_POSTGRES_TESTS_ENABLED=true requis pour RC1 PostgreSQL")


def assert_safe_postgres_url(url: str, *, allow_reset: bool = False) -> str:
    raw = normalize_postgres_url((url or "").strip())

    if not raw:
        raise RuntimeError(
            "ELFIS_PERFORMANCE_DATABASE_URL / --database-url manquant"
        )

    low = raw.lower()

    if low.startswith("sqlite"):
        raise RuntimeError(
            "SQLite interdit pour la validation PostgreSQL RC1"
        )

    if not (
        low.startswith("postgresql")
        or low.startswith("postgres://")
    ):
        raise RuntimeError("URL non PostgreSQL refusée")

    parsed = urlparse(raw)
    host = (parsed.hostname or "").strip().lower()
    name = database_name_from_url(raw)

    environment = assert_safe_rc1_environment()

    has_recette_marker = any(
        marker in name
        for marker in RECETTE_MARKERS
    )

    allow_managed_host = (
        os.getenv("ELFIS_RC1_ALLOW_MANAGED_HOST", "")
        .strip()
        .lower()
        in {"1", "true", "yes"}
    )

    allowed_managed_host = (
        os.getenv("ELFIS_RC1_ALLOWED_MANAGED_HOST", "")
        .strip()
        .lower()
    )

    is_explicit_supabase_staging = all(
        (
            environment in {"staging", "stage"},
            allow_managed_host,
            bool(allowed_managed_host),
            host == allowed_managed_host,
            (host.endswith(".supabase.co") or host.endswith(".supabase.com")),
            name == "postgres",
        )
    )

    if any(marker in name for marker in ("production", "prod")):
        if not has_recette_marker:
            raise RuntimeError(
                "Nom de base ressemble à production — refus RC1"
            )

    if any(marker in low for marker in PROD_MARKERS):
        if not has_recette_marker:
            raise RuntimeError(
                "URL suspecte production — refus RC1"
            )

    is_managed_host = any(
        fragment in host
        for fragment in PROD_HOST_FRAGMENTS
    )

    if is_managed_host and not has_recette_marker:
        if not is_explicit_supabase_staging:
            raise RuntimeError(
                "Hôte managé sans marqueur recette. Pour Supabase staging, "
                "définir ELFIS_RC1_ALLOW_MANAGED_HOST=true et "
                "ELFIS_RC1_ALLOWED_MANAGED_HOST avec l’hôte exact du projet."
            )

    if not has_recette_marker and not is_explicit_supabase_staging:
        raise RuntimeError(
            f"Base {name!r} sans indicateur recette "
            "(test|staging|recette|ci|rc1|functional)"
        )

    if allow_reset:
        reset_enabled = (
            os.getenv("ELFIS_ALLOW_DATABASE_RESET", "")
            .strip()
            .lower()
            in {"1", "true", "yes"}
        )

        if not reset_enabled:
            raise RuntimeError(
                "Reset refusé : ELFIS_ALLOW_DATABASE_RESET=true requis"
            )

        reset_name_allowed = any(
            marker in name
            for marker in ("test", "staging", "recette", "ci", "rc1")
        )

        if not reset_name_allowed and not is_explicit_supabase_staging:
            raise RuntimeError(
                "Reset refusé : cible hors allowlist RC1"
            )

    return raw

def enforce_mocks_env(env: dict[str, str]) -> dict[str, str]:
    """Force mocks / pas de réseau externe pour la campagne RC1."""
    env = dict(env)
    env.setdefault("ELFIS_DISABLE_EXTERNAL_NETWORK", "true")
    env.setdefault("ELFIS_USE_MOCK_AI", "true")
    env.setdefault("ELFIS_USE_MOCK_OCR", "true")
    env.setdefault("ELFIS_USE_MOCK_MAILER", "true")
    env.setdefault("ELFIS_USE_MOCK_STRIPE", "true")
    env.setdefault("ELFIS_USE_MOCK_STORAGE", "true")
    env["OPENAI_API_KEY"] = ""
    env["STRIPE_SECRET_KEY"] = env.get("STRIPE_SECRET_KEY", "")
    if env.get("STRIPE_SECRET_KEY", "").startswith("sk_live"):
        raise RuntimeError("STRIPE_SECRET_KEY live interdit pendant RC1")
    env["BREVO_API_KEY"] = ""
    env.setdefault("ELFIS_OCR_PROVIDER", "disabled")
    env.setdefault("ELFIS_AI_PROVIDER", "mock")
    env.setdefault("ELFIS_BILLING_PROVIDER", "mock")
    return env
