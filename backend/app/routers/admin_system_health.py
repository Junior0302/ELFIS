"""Routes ELFIS Admin — System Health Center (IAM Permission Engine)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.iam.permission_catalog import Permission
from app.iam.permission_context import PermissionContext
from app.iam.permission_dependencies import require_permission
from app.system_health.health_schemas import (
    SystemAlertsResponse,
    SystemHealthSummary,
    SystemLogsResponse,
    SystemMetricsResponse,
)
from app.system_health.health_service import SystemHealthService

router = APIRouter(
    prefix="/admin/system",
    tags=["admin-system-health"],
)


def _service() -> SystemHealthService:
    return SystemHealthService()


@router.get("/health", response_model=SystemHealthSummary)
def admin_system_health(
    _ctx: PermissionContext = Depends(require_permission(Permission.SYSTEM_HEALTH_READ.value)),
    svc: SystemHealthService = Depends(_service),
) -> SystemHealthSummary:
    try:
        from app.audit.audit_logger import AuditLogger

        AuditLogger(isolated_writes=True).record_system_health_refresh(
            actor_user_id=_ctx.user_id,
        )
    except Exception:  # noqa: BLE001
        pass
    return svc.get_summary()


@router.get("/metrics", response_model=SystemMetricsResponse)
def admin_system_metrics(
    period: str = Query(default="24h", pattern=r"^(1h|24h|7d|30d)$"),
    _ctx: PermissionContext = Depends(require_permission(Permission.SYSTEM_METRICS_READ.value)),
    svc: SystemHealthService = Depends(_service),
) -> SystemMetricsResponse:
    return svc.get_metrics(period=period)


@router.get("/alerts", response_model=SystemAlertsResponse)
def admin_system_alerts(
    _ctx: PermissionContext = Depends(require_permission(Permission.SYSTEM_ALERTS_READ.value)),
    svc: SystemHealthService = Depends(_service),
) -> SystemAlertsResponse:
    return svc.get_alerts()


@router.get("/logs", response_model=SystemLogsResponse)
def admin_system_logs(
    limit: int = Query(default=100, ge=1, le=500),
    level: str | None = Query(default=None),
    service_id: str | None = Query(default=None),
    _ctx: PermissionContext = Depends(require_permission(Permission.SYSTEM_LOGS_READ.value)),
    svc: SystemHealthService = Depends(_service),
) -> SystemLogsResponse:
    return svc.get_logs(limit=limit, level=level, service_id=service_id)
