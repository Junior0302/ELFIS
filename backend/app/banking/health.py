"""Banking Health — état des connexions, des fournisseurs et métriques de sync."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.banking.banking_models import ElfisBankConnection, ElfisBankSyncRun
from app.banking.banking_types import ConnectionStatus, SyncRunStatus
from app.banking.engine import BankingEngine
from app.banking.sync_status import needs_reauth


class BankingHealthService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = BankingEngine(db)

    def _run_metrics(self, runs: list[ElfisBankSyncRun]) -> dict:
        finished = [r for r in runs if r.status != SyncRunStatus.running.value]
        failed = [r for r in finished if r.status == SyncRunStatus.failed.value]
        durations = [r.duration_ms for r in finished if r.duration_ms is not None]
        return {
            "runs_total": len(finished),
            "runs_failed": len(failed),
            "failure_rate": round(len(failed) / len(finished), 3) if finished else 0.0,
            "avg_duration_ms": round(sum(durations) / len(durations), 1) if durations else None,
            "last_error": next((r.error_message for r in finished if r.error_message), None),
        }

    def organization_health(self, organization_id: int) -> dict:
        connections = self.engine.list_connections(organization_id)
        provider_health = {h["provider"]: h for h in self.engine.available_connectors()}
        items: list[dict] = []
        for connection in connections:
            runs = (
                self.db.query(ElfisBankSyncRun)
                .filter(ElfisBankSyncRun.connection_id == connection.id)
                .order_by(ElfisBankSyncRun.started_at.desc())
                .limit(20)
                .all()
            )
            metrics = self._run_metrics(runs)
            items.append(
                {
                    "connection_id": connection.id,
                    "provider": connection.provider,
                    "bank_name": connection.bank_name,
                    "status": connection.status,
                    "error_message": connection.error_message,
                    "last_sync_at": connection.last_sync_at,
                    "last_sync_started_at": getattr(connection, "last_sync_started_at", None),
                    "last_sync_status": getattr(connection, "last_sync_status", None) or "never",
                    "last_sync_error_code": getattr(connection, "last_sync_error_code", None),
                    "consecutive_sync_failures": int(
                        getattr(connection, "consecutive_sync_failures", 0) or 0
                    ),
                    "needs_reauth": needs_reauth(connection),
                    "next_sync_at": connection.next_sync_at,
                    "provider_health": provider_health.get(connection.provider),
                    **metrics,
                }
            )
        all_runs = (
            self.db.query(ElfisBankSyncRun)
            .filter(ElfisBankSyncRun.organization_id == organization_id)
            .order_by(ElfisBankSyncRun.started_at.desc())
            .limit(100)
            .all()
        )
        return {
            "connections": items,
            "providers": list(provider_health.values()),
            "summary": self._run_metrics(all_runs),
        }

    def platform_overview(self) -> dict:
        """Vue Cockpit Admin — toutes organisations confondues."""
        connections = self.db.query(ElfisBankConnection).all()
        runs = (
            self.db.query(ElfisBankSyncRun)
            .order_by(ElfisBankSyncRun.started_at.desc())
            .limit(500)
            .all()
        )
        metrics = self._run_metrics(runs)
        recent_errors = [
            {
                "run_id": r.id,
                "organization_id": r.organization_id,
                "connection_id": r.connection_id,
                "provider": r.provider,
                "error_message": r.error_message,
                "started_at": r.started_at,
                "attempt_count": r.attempt_count,
            }
            for r in runs
            if r.status == SyncRunStatus.failed.value
        ][:20]
        by_provider: dict[str, dict] = {}
        for connection in connections:
            slot = by_provider.setdefault(
                connection.provider,
                {"provider": connection.provider, "connections": 0, "connected": 0, "errors": 0},
            )
            slot["connections"] += 1
            if connection.status == ConnectionStatus.connected.value:
                slot["connected"] += 1
            if connection.status == ConnectionStatus.error.value:
                slot["errors"] += 1
        return {
            "connections_total": len(connections),
            "connections_active": sum(
                1 for c in connections if c.status == ConnectionStatus.connected.value
            ),
            "connections_error": sum(
                1 for c in connections if c.status == ConnectionStatus.error.value
            ),
            "by_provider": sorted(by_provider.values(), key=lambda x: x["provider"]),
            "recent_errors": recent_errors,
            **metrics,
        }
