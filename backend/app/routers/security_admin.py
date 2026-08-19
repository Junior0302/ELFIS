"""Routes plateforme — sécurité / observabilité / fiabilité."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_platform_admin
from app.models_saas import User
from app.observability.metrics import metrics_registry
from app.reliability.backup_policy import backup_policy
from app.reliability.cleanup_service import CleanupService
from app.reliability.recovery_policy import recovery_policy
from app.reliability.readiness_service import ReadinessService
from app.reliability.retention_service import RetentionService
from app.security.security_audit import list_security_events
from app.security.security_startup import configuration_public_view

router = APIRouter(
    prefix="/platform",
    tags=["platform-security-observability"],
    dependencies=[Depends(require_platform_admin)],
)


@router.get("/security/events")
def platform_security_events(
    event_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    return {"events": list_security_events(db, event_type=event_type, limit=limit)}


@router.get("/security/configuration")
def platform_security_configuration(_admin: User = Depends(require_platform_admin)):
    return configuration_public_view()


@router.get("/observability/metrics")
def platform_observability_metrics(_admin: User = Depends(require_platform_admin)):
    return {"format": "json", "metrics": metrics_registry.snapshot()}


@router.get("/observability/health")
def platform_observability_health(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    return ReadinessService(db).details()


@router.get("/reliability/retention")
def platform_reliability_retention(_admin: User = Depends(require_platform_admin)):
    return {"policies": RetentionService().policies()}


@router.post("/reliability/cleanup/dry-run")
def platform_reliability_cleanup_dry_run(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    return CleanupService(db).run(force_dry_run=True)


@router.get("/reliability/readiness")
def platform_reliability_readiness(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    svc = ReadinessService(db)
    return {
        "ready": svc.readiness(),
        "stale_jobs": svc.detect_stale_jobs(),
        "stale_events": svc.detect_stale_events(),
    }


@router.get("/reliability/backup-policy")
def platform_reliability_backup_policy(_admin: User = Depends(require_platform_admin)):
    return {
        "backup": backup_policy(),
        "recovery": recovery_policy(),
    }
