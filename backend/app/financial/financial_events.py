"""Publication des événements Financial — consommés par l'AI Financial Assistant.

Convention plateforme ``module.entity.action.vN`` :
- financial.health.updated.v1 : le Health Score a changé
- financial.alert.created.v1  : une nouvelle alerte normalisée est levée
- financial.kpi.updated.v1    : les KPIs recalculés ont changé
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.financial.financial_types import FinancialAlert


def _publish(
    db: Session,
    *,
    event_name: str,
    organization_id: int,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict,
    idempotency_key: str,
) -> None:
    safe_publish(
        db,
        DomainEvent(
            event_name=event_name,
            organization_id=organization_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            metadata={"source": "financial_dashboard_v1"},
            idempotency_key=idempotency_key,
            correlation_id=uuid.uuid4(),
        ),
    )


def publish_health_updated(
    db: Session,
    *,
    organization_id: int,
    score: float,
    grade: str,
    components: list[dict],
    fingerprint: str,
) -> None:
    _publish(
        db,
        event_name=EventNames.FINANCIAL_HEALTH_UPDATED,
        organization_id=organization_id,
        aggregate_type="financial_health",
        aggregate_id=str(organization_id),
        payload={
            "score": score,
            "grade": grade,
            "components": components,
        },
        idempotency_key=f"financial-health-{organization_id}-{fingerprint}",
    )


def publish_alert_created(db: Session, *, organization_id: int, alert: FinancialAlert) -> None:
    _publish(
        db,
        event_name=EventNames.FINANCIAL_ALERT_CREATED,
        organization_id=organization_id,
        aggregate_type="financial_alert",
        aggregate_id=alert.id,
        payload={
            "code": alert.code,
            "severity": alert.severity.value,
            "title": alert.title,
            "message": alert.message,
            "action": alert.action,
            "value": alert.value,
        },
        # une même alerte n'est publiée qu'une fois par jour et par organisation
        idempotency_key=f"financial-alert-{organization_id}-{alert.code}-{date.today().isoformat()}",
    )


def publish_kpis_updated(
    db: Session,
    *,
    organization_id: int,
    kpis: list[dict],
    fingerprint: str,
) -> None:
    _publish(
        db,
        event_name=EventNames.FINANCIAL_KPI_UPDATED,
        organization_id=organization_id,
        aggregate_type="financial_kpis",
        aggregate_id=str(organization_id),
        payload={"kpis": kpis},
        idempotency_key=f"financial-kpis-{organization_id}-{fingerprint}",
    )
