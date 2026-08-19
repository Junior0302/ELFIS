"""PERF — Search baseline."""

from __future__ import annotations

import pytest

from tests.functional.helpers.phase_a import seed_search_document
from tests.performance.helpers import measure_latencies, performance_enabled

pytestmark = pytest.mark.skipif(not performance_enabled(), reason="ELFIS_PERFORMANCE_TESTS_ENABLED=false")


def test_perf_003_search_baseline(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        seed_search_document(db, org_id=org_id, unique_term="perfphasefsearch")
    finally:
        db.close()

    api.login_user("org_admin")

    def call():
        r = api.client.get("/api/search?q=perfphasefsearch&page=1&page_size=20", headers=api._headers())
        assert r.status_code in (200, 403, 503)
        return r

    stats = measure_latencies(call, rounds=8, warmup=1)
    assert stats["errors"] == 0
    if stats["p95_ms"] is not None:
        assert stats["p95_ms"] < 5000
