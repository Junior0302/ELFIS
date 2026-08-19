"""Registry Accounting — réservé extensions futures (export FEC, etc.)."""

from __future__ import annotations


class AccountingExportRegistry:
    """Interface minimale — aucun export réel en V1."""

    def __init__(self) -> None:
        self._exporters: dict[str, object] = {}

    def register(self, name: str, exporter: object) -> None:
        self._exporters[name] = exporter

    def has(self, name: str) -> bool:
        return name in self._exporters


default_export_registry = AccountingExportRegistry()
