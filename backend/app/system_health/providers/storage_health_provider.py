"""Provider réel System Health — Storage Abstraction (RC2.4 étape 2)."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from app.config import settings
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_registry import build_storage_provider, clear_storage_provider_cache
from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult
from app.system_health.health_thresholds import HealthThresholds, load_thresholds
from app.system_health.health_types import HealthCategory, HealthStatus
from app.system_health.health_utils import metric, run_with_timeout, safe_error_message, utcnow

logger = logging.getLogger(__name__)


class StorageHealthProvider(HealthProvider):
    service_id = "storage"
    service_name = "Storage"
    category = HealthCategory.STORAGE.value

    def __init__(
        self,
        *,
        thresholds: HealthThresholds | None = None,
        timeout_seconds: float | None = None,
        provider_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._thresholds = thresholds or load_thresholds()
        configured_timeout = getattr(settings, "storage_probe_timeout_seconds", None)
        self._timeout = (
            float(timeout_seconds)
            if timeout_seconds is not None
            else float(configured_timeout or self._thresholds.provider_timeout_seconds)
        )
        self._provider_factory = provider_factory

    def check_health(self) -> HealthCheckResult:
        try:
            return run_with_timeout(self._check, timeout_seconds=self._timeout, label=self.service_id)
        except Exception as exc:
            logger.warning("system_health_storage_failed", extra={"error": type(exc).__name__})
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=HealthStatus.UNHEALTHY,
                summary="Storage inaccessible",
                latency_ms=None,
                checked_at=utcnow(),
                version="v1",
                metrics=[],
                metadata={"provider_mode": "real", "simulated": False},
                error_code="storage_check_failed",
                error_message=safe_error_message(exc),
            )

    def _check(self) -> HealthCheckResult:
        t0 = time.perf_counter()
        configured = (getattr(settings, "storage_provider", "local") or "local").strip().lower()
        clear_storage_provider_cache()
        provider = self._provider_factory() if self._provider_factory else build_storage_provider()

        if provider.name == "disabled" or configured == "disabled":
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=HealthStatus.DEGRADED,
                summary="Storage provider disabled",
                latency_ms=latency_ms,
                checked_at=utcnow(),
                version="v1",
                metrics=[
                    metric("provider", "Provider", "disabled"),
                    metric("probe_ok", "Probe", "false"),
                ],
                metadata={
                    "provider_mode": "real",
                    "simulated": False,
                    "storage_provider": "disabled",
                },
                error_code="storage_disabled",
                error_message="STORAGE_PROVIDER=disabled",
            )

        probe = provider.health_check()
        probe_ok = bool(probe.get("probe_ok"))
        stream_ok = bool(probe.get("stream_ok", probe_ok))
        status_raw = str(probe.get("status") or "").lower()
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        used_ratio = probe.get("used_ratio")
        degraded_pct = float(getattr(settings, "storage_disk_degraded_percent", 85) or 85) / 100.0
        unhealthy_pct = float(getattr(settings, "storage_disk_unhealthy_percent", 95) or 95) / 100.0

        if probe.get("root_accessible") is False:
            status = HealthStatus.UNHEALTHY
            summary = "Répertoire storage inaccessible"
            error_code = "storage_root_inaccessible"
            error_message = "Racine locale inaccessible"
        elif not probe_ok or status_raw != "healthy":
            status = HealthStatus.UNHEALTHY
            summary = "Probe storage échoué"
            error_code = "storage_probe_failed"
            error_message = str(probe.get("error") or "probe_failed")[:200]
        elif used_ratio is not None and used_ratio >= unhealthy_pct:
            status = HealthStatus.UNHEALTHY
            summary = "Espace disque critique"
            error_code = "storage_disk_unhealthy"
            error_message = "Seuil disque unhealthy atteint"
        elif used_ratio is not None and used_ratio >= degraded_pct:
            status = HealthStatus.DEGRADED
            summary = "Espace disque faible"
            error_code = "storage_disk_degraded"
            error_message = "Seuil disque degraded atteint"
        elif status_raw == "degraded":
            status = HealthStatus.DEGRADED
            summary = "Storage dégradé"
            error_code = "storage_degraded"
            error_message = str(probe.get("error") or "degraded")[:200]
        else:
            status = HealthStatus.HEALTHY
            summary = (
                "Storage Supabase opérationnel"
                if provider.name == "supabase"
                else "Storage local opérationnel"
            )
            error_code = None
            error_message = None

        metrics = [
            metric("provider", "Provider", provider.name),
            metric("probe_ok", "Probe", "true" if probe_ok else "false"),
            metric("stream_ok", "Stream", "true" if stream_ok else "false"),
            metric("latency_ms", "Latence", probe.get("latency_ms") or latency_ms, unit="ms"),
            metric("free_bytes", "Espace libre", probe.get("free_bytes"), unit="bytes"),
            metric("used_ratio", "Occupation", used_ratio),
            metric("old_temp_count", "Temporaires anciens", probe.get("old_temp_count"), unit="files"),
        ]
        meta: dict[str, Any] = {
            "provider_mode": "real",
            "simulated": False,
            "storage_provider": provider.name,
            "root_configured": bool(
                getattr(settings, "storage_local_root", None) or settings.storage_dir
            ),
            "probe_ok": probe_ok,
            "stream_ok": stream_ok,
        }
        # Jamais de chemin absolu
        if isinstance(provider, LocalStorageProvider):
            meta["temp_namespace"] = "_temp"

        return HealthCheckResult(
            service_id=self.service_id,
            service_name=self.service_name,
            category=self.category,
            status=status,
            summary=summary,
            latency_ms=latency_ms,
            checked_at=utcnow(),
            version="v1",
            metrics=metrics,
            metadata=meta,
            error_code=error_code,
            error_message=error_message,
        )
