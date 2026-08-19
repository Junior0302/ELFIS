"""Schémas Pydantic — System Health Center."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.system_health.health_types import AlertSeverity, HealthStatus


class HealthMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    value: int | float | str | None = None
    unit: str | None = None
    status: str | None = None
    description: str | None = None
    timestamp: datetime


class HealthCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: str
    service_name: str
    category: str
    status: HealthStatus
    summary: str
    latency_ms: float | None = None
    checked_at: datetime
    version: str | None = None
    metrics: list[HealthMetric] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


class SystemHealthSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_status: HealthStatus
    generated_at: datetime
    environment: str
    platform_version: str | None = None
    healthy_count: int
    degraded_count: int
    unhealthy_count: int
    unknown_count: int
    services: list[HealthCheckResult]


class SystemAlert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str
    severity: AlertSeverity
    service_id: str | None = None
    title: str
    message: str
    impact: str | None = None
    recommendation: str | None = None
    started_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None = None
    is_active: bool = True


class SystemLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    log_id: str
    timestamp: datetime
    level: str
    service_id: str | None = None
    event_type: str
    message: str
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SystemMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    period: str
    metrics: list[HealthMetric]


class SystemAlertsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    active_count: int
    critical_count: int
    warning_count: int
    alerts: list[SystemAlert]


class SystemLogsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    total: int
    entries: list[SystemLogEntry]
