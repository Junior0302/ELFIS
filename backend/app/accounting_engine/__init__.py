"""Accounting Engine V2 — propositions comptables (aucune écriture définitive)."""

from __future__ import annotations

__all__ = ["AccountingEngine"]


def __getattr__(name: str):
    if name == "AccountingEngine":
        from app.accounting_engine.engine import AccountingEngine

        return AccountingEngine
    raise AttributeError(name)
