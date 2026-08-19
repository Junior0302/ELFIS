"""Routes health / metrics publiques (protégées selon config)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import require_platform_admin
from app.models_saas import User
from app.observability.health import details, live, ready
from app.observability.metrics import metrics_registry

router = APIRouter(tags=["observability"])


@router.get("/health/live")
def health_live():
    return live()


@router.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    result = ready(db)
    status_code = 200 if result.get("status") in {"ok", "degraded"} else 503
    from fastapi.responses import JSONResponse

    return JSONResponse(content=result, status_code=status_code)


@router.get("/health/details")
def health_details(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    return details(db)


def _authorize_metrics(
    authorization: str | None,
    x_metrics_token: str | None,
    db: Session,
) -> None:
    if not getattr(settings, "elfis_metrics_enabled", True):
        raise HTTPException(404, detail={"code": "not_found", "message": "Metrics désactivées"})
    if not getattr(settings, "elfis_metrics_require_auth", True):
        return
    expected = (getattr(settings, "elfis_metrics_token", "") or "").strip()
    if expected and x_metrics_token and x_metrics_token == expected:
        return
    require_platform_admin(authorization=authorization, db=db)


@router.get("/metrics")
def metrics_json(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_metrics_token: str | None = Header(default=None, alias="X-Metrics-Token"),
):
    _authorize_metrics(authorization, x_metrics_token, db)
    return {"format": "json", "metrics": metrics_registry.snapshot()}
