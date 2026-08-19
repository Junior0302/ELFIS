"""Tests du cache TTL du Financial Engine."""

from __future__ import annotations

from app.financial.cache import KeyedTtlCache, reset_change_tracking, snapshot_cache, value_changed
from app.financial.engine import FinancialEngine

from tests.financial.helpers import make_financial_db, seed_finance_data, seed_org


def test_snapshot_is_cached_between_calls():
    db = make_financial_db()
    org = seed_org(db)
    data = seed_finance_data(db, org.id)

    engine = FinancialEngine(db, publish_events=False)
    first = engine.snapshot(org.id)

    # modification en base non visible tant que le cache est chaud
    data["account"].balance = 99999.0
    db.commit()
    cached = engine.snapshot(org.id)
    assert cached["treasury"] == first["treasury"]
    assert cached["computed_at"] == first["computed_at"]


def test_refresh_bypasses_cache():
    db = make_financial_db()
    org = seed_org(db)
    data = seed_finance_data(db, org.id)

    engine = FinancialEngine(db, publish_events=False)
    engine.snapshot(org.id)

    data["account"].balance = 99999.0
    db.commit()
    refreshed = engine.snapshot(org.id, refresh=True)
    assert refreshed["treasury"] == 99999.0


def test_invalidate_clears_organization_entry():
    db = make_financial_db()
    org = seed_org(db)
    data = seed_finance_data(db, org.id)

    engine = FinancialEngine(db, publish_events=False)
    engine.snapshot(org.id)
    data["account"].balance = 42000.0
    db.commit()

    engine.invalidate(org.id)
    assert engine.snapshot(org.id)["treasury"] == 42000.0


def test_cache_is_keyed_by_organization():
    db = make_financial_db()
    org_a = seed_org(db, "Org A")
    org_b = seed_org(db, "Org B")
    seed_finance_data(db, org_a.id)

    engine = FinancialEngine(db, publish_events=False)
    assert engine.snapshot(org_a.id)["treasury"] == 12000.0
    assert engine.snapshot(org_b.id)["treasury"] == 0.0


def test_keyed_ttl_cache_expires():
    import time

    cache = KeyedTtlCache(ttl_seconds=0.01)
    cache.set("k", {"v": 1})
    time.sleep(0.03)
    assert cache.get("k") is None

    cache_long = KeyedTtlCache(ttl_seconds=60.0)
    cache_long.set("k", {"v": 2})
    assert cache_long.get("k") == {"v": 2}
    cache_long.clear()
    assert cache_long.get("k") is None


def test_value_changed_tracks_fingerprints():
    reset_change_tracking()
    assert value_changed("kpis-1", "abc") is True
    assert value_changed("kpis-1", "abc") is False
    assert value_changed("kpis-1", "def") is True


def test_shared_snapshot_cache_default_ttl_from_settings():
    from app.config import settings

    assert snapshot_cache.ttl_seconds == float(settings.financial_cache_ttl_seconds)
