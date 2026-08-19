"""Politique de sauvegarde — documentation + état, sans pg_dump HTTP."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.security.security_config import is_production


def backup_policy() -> dict[str, Any]:
    return {
        "version": "v1",
        "automated_from_api": False,
        "postgresql": {
            "method": "pg_dump / snapshot provider",
            "frequency_recommended": "daily",
            "encryption": "at-rest by provider + optional GPG offline",
            "retention_days_recommended": 30,
            "integrity_check": "restore test monthly",
            "configured": not settings.database_url.startswith("sqlite") if is_production() else True,
            "source": "environment",
            "status": "valid" if (not is_production() or "postgres" in settings.database_url or "postgresql" in settings.database_url) else "warning",
        },
        "vault_storage": {
            "method": "bucket versioning / cross-region replica (provider)",
            "configured": bool(settings.supabase_url),
            "source": "environment",
            "status": "valid" if settings.supabase_url or not is_production() else "warning",
            "secrets_excluded": True,
        },
        "secrets": {
            "method": "rotate via env / secret manager — never in DB backup alone",
            "configured": True,
            "status": "valid",
        },
        "notes": [
            "Aucune route HTTP n'exécute pg_dump.",
            "Tester la restauration hors production avant incident.",
            "Séparer backups staging et production.",
        ],
    }
