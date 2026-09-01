"""CORS — localhost hors production uniquement."""

from __future__ import annotations

from app.security.cors_policy import resolve_cors_allow_origins


def test_production_uses_only_explicit_https_origins():
    origins = resolve_cors_allow_origins(
        cors_origins="https://elfis-core.web.app,http://localhost:5173,*",
        frontend_url="https://elfis-core.web.app",
        production=True,
    )
    assert origins == ["https://elfis-core.web.app"]
    assert all(item.startswith("https://") for item in origins)
    assert not any("localhost" in item or "127.0.0.1" in item for item in origins)
    assert "*" not in origins


def test_production_allows_firebase_hosting_origins():
    origins = resolve_cors_allow_origins(
        cors_origins="https://elfis-core.web.app,https://elfis-core.firebaseapp.com",
        frontend_url="https://elfis-core.web.app",
        production=True,
    )
    assert "https://elfis-core.web.app" in origins
    assert "https://elfis-core.firebaseapp.com" in origins
    assert "*" not in origins


def test_production_adds_https_frontend_url():
    origins = resolve_cors_allow_origins(
        cors_origins="https://elfis-core.web.app",
        frontend_url="https://demo.elfis-core.com",
        production=True,
    )
    assert origins == ["https://elfis-core.web.app", "https://demo.elfis-core.com"]


def test_production_rejects_localhost_frontend_url():
    origins = resolve_cors_allow_origins(
        cors_origins="https://elfis-core.web.app",
        frontend_url="http://localhost:5173",
        production=True,
    )
    assert origins == ["https://elfis-core.web.app"]


def test_development_keeps_localhost_and_wildcard():
    wildcard = resolve_cors_allow_origins(
        cors_origins="*",
        frontend_url="http://localhost:5173",
        production=False,
    )
    assert wildcard == ["*"]

    explicit = resolve_cors_allow_origins(
        cors_origins="http://localhost:5173",
        frontend_url="http://127.0.0.1:5173",
        production=False,
    )
    assert "http://localhost:5173" in explicit
    assert "http://127.0.0.1:5173" in explicit
