"""SCENARIO 11/12 — Sécurité, corrélation, erreurs."""

from __future__ import annotations


def test_request_and_correlation_ids(api):
    r = api.client.get(
        "/api/health/live",
        headers={"X-Request-Id": "func-req-id-123456", "X-Correlation-Id": "func-corr-id-999999"},
    )
    assert r.status_code == 200
    assert r.headers.get("X-Request-Id") == "func-req-id-123456"
    assert r.headers.get("X-Correlation-Id") == "func-corr-id-999999"


def test_normalized_error_on_unauthorized(api):
    r = api.client.get("/api/platform/dashboard")
    assert r.status_code in (401, 403)
    body = r.json()
    assert "error" in body
    assert body["error"].get("code")
    assert body["error"].get("request_id")
    assert "traceback" not in str(body).lower()


def test_security_headers_present(api):
    r = api.client.get("/api/health/live")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"


def test_mock_ai_retry_then_success():
    from tests.functional.fixtures.mock_providers import MockAIProvider

    ai = MockAIProvider()
    ai.mode = "temporary"
    try:
        ai.complete()
        assert False
    except TimeoutError:
        pass
    # 2e appel réussit
    out = ai.complete()
    assert out.confidence > 0.5
    assert ai.calls == 2
