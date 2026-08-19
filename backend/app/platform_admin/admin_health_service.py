"""Santé des services — vérifications locales (pas d'appel réseau coûteux)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.platform_admin.admin_types import ServiceHealthStatus


class AdminHealthService:
    def __init__(self, db: Session):
        self.db = db

    def check_all(self) -> dict[str, Any]:
        services = [
            self._database(),
            self._flag("vault", bool(settings.supabase_url and settings.supabase_service_role_key)),
            self._flag("event_bus", True, note="Bus DB local"),
            self._flag("job_queue", True, note="Queue DB locale"),
            self._flag("notifications", True),
            self._mailer(),
            self._flag("delivery", True),
            self._flag(
                "document_intelligence",
                bool(settings.elfis_document_intelligence_enabled),
            ),
            self._flag(
                "ocr",
                bool(settings.elfis_ocr_enabled),
                disabled_message="OCR désactivé",
            ),
            self._flag("ai", bool(settings.elfis_ai_enabled and settings.openai_api_key)),
            self._flag("accounting", bool(settings.elfis_accounting_pipeline_enabled)),
            self._flag("search", bool(settings.elfis_search_enabled)),
            self._flag("billing", bool(settings.elfis_billing_enabled)),
            self._stripe(),
        ]
        return {"checked_at": datetime.utcnow().isoformat() + "Z", "services": services}

    def _item(
        self,
        service: str,
        status: str,
        message: str,
        metrics: dict | None = None,
    ) -> dict[str, Any]:
        return {
            "service": service,
            "status": status,
            "message": message,
            "checked_at": datetime.utcnow().isoformat() + "Z",
            "metrics": metrics or {},
        }

    def _database(self) -> dict[str, Any]:
        try:
            self.db.execute(text("SELECT 1"))
            return self._item("database", ServiceHealthStatus.HEALTHY, "Base accessible")
        except Exception as exc:
            return self._item(
                "database",
                ServiceHealthStatus.UNAVAILABLE,
                f"Erreur base: {type(exc).__name__}",
            )

    def _flag(
        self,
        name: str,
        enabled: bool,
        *,
        note: str = "",
        disabled_message: str = "Service désactivé",
    ) -> dict[str, Any]:
        if not enabled:
            return self._item(name, ServiceHealthStatus.DISABLED, disabled_message)
        return self._item(name, ServiceHealthStatus.HEALTHY, note or "Configuré / actif")

    def _mailer(self) -> dict[str, Any]:
        from app.services.mailer import email_configured

        if email_configured():
            return self._item("mailer", ServiceHealthStatus.HEALTHY, "Transport e-mail configuré")
        return self._item("mailer", ServiceHealthStatus.DEGRADED, "E-mail non configuré")

    def _stripe(self) -> dict[str, Any]:
        configured = bool(settings.stripe_secret_key and settings.stripe_price_pro)
        if configured:
            return self._item(
                "stripe",
                ServiceHealthStatus.HEALTHY,
                "Configuration locale Stripe présente (pas d'appel réseau)",
                {"webhook_configured": bool(settings.stripe_webhook_secret)},
            )
        return self._item("stripe", ServiceHealthStatus.DISABLED, "Stripe non configuré")
