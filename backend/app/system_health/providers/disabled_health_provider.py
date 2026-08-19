"""Provider désactivé explicitement (mode disabled)."""

from __future__ import annotations

from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult
from app.system_health.health_types import HealthStatus
from app.system_health.health_utils import utcnow


class DisabledHealthProvider(HealthProvider):
    def __init__(
        self,
        *,
        service_id: str,
        service_name: str,
        category: str,
        reason: str = "Provider désactivé par configuration",
    ) -> None:
        self.service_id = service_id
        self.service_name = service_name
        self.category = category
        self._reason = reason

    def check_health(self) -> HealthCheckResult:
        return HealthCheckResult(
            service_id=self.service_id,
            service_name=self.service_name,
            category=self.category,
            status=HealthStatus.DISABLED,
            summary=self._reason,
            latency_ms=None,
            checked_at=utcnow(),
            version=None,
            metrics=[],
            metadata={"provider_mode": "disabled"},
            error_code="provider_disabled",
            error_message=self._reason,
        )
