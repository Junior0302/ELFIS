"""Smart Migration Engine — orchestration Enterprise (Sprint 7)."""

from __future__ import annotations

__all__ = ["SmartMigrationOrchestrator"]


def __getattr__(name: str):
    if name == "SmartMigrationOrchestrator":
        from app.smart_migration.orchestrator import SmartMigrationOrchestrator

        return SmartMigrationOrchestrator
    raise AttributeError(name)
