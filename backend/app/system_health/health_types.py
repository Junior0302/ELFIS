"""Types et constantes System Health — pas de chaînes magiques dispersées."""

from __future__ import annotations

from enum import Enum


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    DISABLED = "disabled"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class HealthCategory(str, Enum):
    PLATFORM = "platform"
    DATA = "data"
    WORKERS = "workers"
    SEARCH = "search"
    BILLING = "billing"
    COMMUNICATION = "communication"
    SECURITY = "security"
    STORAGE = "storage"
    AI = "ai"
    OCR = "ocr"


# Ordre de sévérité pour agrégation overall
STATUS_SEVERITY_ORDER: tuple[HealthStatus, ...] = (
    HealthStatus.UNHEALTHY,
    HealthStatus.DEGRADED,
    HealthStatus.UNKNOWN,
    HealthStatus.DISABLED,
    HealthStatus.HEALTHY,
)
