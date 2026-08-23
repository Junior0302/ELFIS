"""Types normalisés du Financial Engine — KPIs, tendances, alertes, séries."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class KpiStatus(str, Enum):
    ok = "ok"
    warning = "warning"
    critical = "critical"
    neutral = "neutral"


class TrendDirection(str, Enum):
    up = "up"
    down = "down"
    flat = "flat"


class KpiTrend(BaseModel):
    """Comparaison homogène avec la période précédente."""

    direction: TrendDirection = TrendDirection.flat
    delta: float = 0.0
    delta_pct: float | None = None
    previous: float = 0.0


class Kpi(BaseModel):
    """Indicateur standardisé — tous les KPI partagent exactement ce format."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    value: float | None
    unit: str  # "EUR" | "count"
    format: str  # "currency" | "integer"
    status: KpiStatus = KpiStatus.neutral
    trend: KpiTrend = Field(default_factory=KpiTrend)
    hint: str = ""


class AlertSeverity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class FinancialAlert(BaseModel):
    """Alerte normalisée produite par le moteur d'alertes."""

    model_config = ConfigDict(extra="forbid")

    id: str
    code: str
    severity: AlertSeverity
    title: str
    message: str
    action: str = ""
    source: str = "financial_engine"
    value: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TrendPoint(BaseModel):
    period: str  # "2026-07" | "2026-S30" | "2026"
    label: str
    revenue: float = 0.0
    expenses: float = 0.0
    result: float = 0.0


class SeriesPoint(BaseModel):
    label: str
    value: float


class HealthComponent(BaseModel):
    id: str
    label: str
    score: float
    max_score: float
    detail: str = ""


def parse_flexible_date(raw: str | None) -> date | None:
    """Parse les dates hétérogènes du système (ISO, JJ-MM-AAAA, JJ/MM/AAAA)."""
    if not raw:
        return None
    text = str(raw).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
