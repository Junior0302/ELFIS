"""HEALTH / readiness."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.observability.health import live, ready


def test_health_001_liveness():
    result = live()
    assert result["status"] == "ok"
    assert result["check"] == "live"


def test_health_002_readiness_ok_with_mock_db(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "database_url", "sqlite:///./x.db")
    monkeypatch.setattr(settings, "elfis_environment", "test")

    db = MagicMock()
    # SELECT 1
    db.execute.return_value.fetchone.return_value = ("users",)

    # ready() appelle execute plusieurs fois — simplifier via side_effect
    def _exec(stmt, params=None):
        m = MagicMock()
        text = str(stmt)
        if "sqlite_master" in text or "to_regclass" in text:
            m.fetchone.return_value = (params.get("n") if params else "users",)
        else:
            m.fetchone.return_value = (1,)
        return m

    db.execute.side_effect = _exec
    result = ready(db)
    assert result["check"] == "ready"
    assert result["status"] in {"ok", "degraded"}


def test_health_003_readiness_db_failure():
    db = MagicMock()
    db.execute.side_effect = RuntimeError("connection refused")
    result = ready(db)
    assert result["status"] == "error"
    assert result["checks"]["database"]["status"] == "error"
