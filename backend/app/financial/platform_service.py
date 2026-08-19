"""Vue plateforme du Financial Engine — Cockpit Admin.

Agrège la santé financière de toutes les organisations : score moyen,
organisations sans synchronisation bancaire, alertes critiques, statistiques
globales.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.financial.alerts import build_alerts
from app.financial.engine import FinancialEngine
from app.financial.financial_types import AlertSeverity
from app.financial.health import compute_health_score
from app.models_saas import Organization

MAX_ORGANIZATIONS = 500


class FinancialPlatformService:
    def __init__(self, db: Session):
        self.db = db
        # pas de publication d'événements depuis la vue admin (lecture seule)
        self.engine = FinancialEngine(db, publish_events=False)

    def platform_overview(self) -> dict:
        orgs = self.db.query(Organization).limit(MAX_ORGANIZATIONS).all()

        scores: list[float] = []
        organizations: list[dict] = []
        without_sync = 0
        sync_errors = 0
        critical_alerts = 0
        warning_alerts = 0
        setup_count = 0

        for org in orgs:
            snap = self.engine.snapshot(org.id)
            health = compute_health_score(snap)
            alerts = build_alerts(snap)
            crit = sum(1 for a in alerts if a.severity == AlertSeverity.critical)
            warn = sum(1 for a in alerts if a.severity == AlertSeverity.warning)
            critical_alerts += crit
            warning_alerts += warn

            sync = snap["sync"]
            no_sync = sync["status"] in {"none", "stale", "error"}
            if no_sync and snap["has_data"]:
                without_sync += 1
            sync_errors += sync["errors"]

            if health["state"] == "setup":
                setup_count += 1
            elif health["score"] is not None:
                scores.append(health["score"])

            organizations.append(
                {
                    "organization_id": org.id,
                    "name": org.name,
                    "score": health["score"],
                    "grade": health["grade"],
                    "state": health["state"],
                    "treasury": snap["treasury"],
                    "revenue": snap["revenue"],
                    "sync_status": sync["status"],
                    "critical_alerts": crit,
                    "warning_alerts": warn,
                }
            )

        organizations.sort(key=lambda o: (o["score"] is None, o["score"] or 0.0))
        return {
            "organizations_total": len(orgs),
            "organizations_active": len(scores),
            "organizations_setup": setup_count,
            "average_score": round(sum(scores) / len(scores), 1) if scores else None,
            "organizations_without_sync": without_sync,
            "sync_errors": sync_errors,
            "critical_alerts": critical_alerts,
            "warning_alerts": warning_alerts,
            "organizations": organizations[:50],
        }
