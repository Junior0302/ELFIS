"""Import Engine V1 — Migration Center Sprint 6."""

from __future__ import annotations

__all__ = ["ImportEngineService"]


def __getattr__(name: str):
    if name == "ImportEngineService":
        from app.import_engine.service import ImportEngineService

        return ImportEngineService
    raise AttributeError(name)
