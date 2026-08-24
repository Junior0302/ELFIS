"""Tests StorageHealthProvider."""

from __future__ import annotations

from pathlib import Path

from app.storage.providers.disabled_storage_provider import DisabledStorageProvider
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.system_health.health_types import HealthStatus
from app.system_health.providers.storage_health_provider import StorageHealthProvider


def test_local_healthy(tmp_path, monkeypatch):
    root = tmp_path / "ok"
    root.mkdir()
    monkeypatch.setattr("app.config.settings.storage_provider", "local")
    monkeypatch.setattr("app.config.settings.storage_disk_degraded_percent", 99.9)
    monkeypatch.setattr("app.config.settings.storage_disk_unhealthy_percent", 99.95)
    provider = StorageHealthProvider(
        provider_factory=lambda: LocalStorageProvider(root=root),
        timeout_seconds=5,
    )
    result = provider.check_health()
    assert result.status == HealthStatus.HEALTHY
    assert result.metadata["probe_ok"] is True
    assert list(root.rglob("*.probe")) == []
    # pas de chemin absolu dans metadata
    assert str(root) not in str(result.metadata)


def test_disabled_degraded(monkeypatch):
    monkeypatch.setattr("app.config.settings.storage_provider", "disabled")
    provider = StorageHealthProvider(
        provider_factory=lambda: DisabledStorageProvider(),
        timeout_seconds=5,
    )
    result = provider.check_health()
    assert result.status == HealthStatus.DEGRADED
    assert result.error_code == "storage_disabled"


def test_inaccessible_root(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.storage_provider", "local")
    missing = tmp_path / "missing" / "nested"

    class Broken(LocalStorageProvider):
        def __init__(self):
            # bypass mkdir — simuler root inaccessible via health_check
            self._root = missing
            self.name = "local"

        def health_check(self):
            return {
                "provider": "local",
                "status": "unhealthy",
                "root_accessible": False,
                "probe_ok": False,
                "error": "PermissionError",
            }

    provider = StorageHealthProvider(provider_factory=Broken, timeout_seconds=5)
    result = provider.check_health()
    assert result.status == HealthStatus.UNHEALTHY
    assert result.error_code == "storage_root_inaccessible"


def test_probe_failed(monkeypatch):
    monkeypatch.setattr("app.config.settings.storage_provider", "local")

    class FailProbe(LocalStorageProvider):
        def __init__(self):
            self._root = Path(".")
            self.name = "local"

        def health_check(self):
            return {
                "provider": "local",
                "status": "unhealthy",
                "root_accessible": True,
                "probe_ok": False,
                "error": "IOError",
            }

    provider = StorageHealthProvider(provider_factory=FailProbe, timeout_seconds=5)
    result = provider.check_health()
    assert result.status == HealthStatus.UNHEALTHY
    assert result.error_code == "storage_probe_failed"
