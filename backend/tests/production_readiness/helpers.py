"""Helpers Phase G — production readiness."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.security.security_startup import ConfigIssue, validate_runtime_configuration


def issues_for_production_simulation(monkeypatch, **overrides: Any) -> list[ConfigIssue]:
    """Simule un environnement production pour valider les garde-fous (sans démarrer l’app)."""
    monkeypatch.setattr(settings, "elfis_environment", "production")
    monkeypatch.setattr(settings, "app_env", "production")
    for key, value in overrides.items():
        monkeypatch.setattr(settings, key, value)
    return validate_runtime_configuration()


def fatal_codes(issues: list[ConfigIssue]) -> set[str]:
    return {i.code for i in issues if i.level == "fatal"}
