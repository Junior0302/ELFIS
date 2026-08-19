"""SCENARIO 6 — Delivery / mailer mock."""

from __future__ import annotations

from tests.functional.fixtures.mock_providers import MockMailerProvider


def test_mock_mailer_outbox():
    mailer = MockMailerProvider()
    mailer.send(to="client.fictif@test.elfis.local", subject="Facture", body="Votre facture")
    assert len(mailer.outbox) == 1
    assert mailer.outbox[0].status == "sent"
    assert mailer.outbox[0].to.endswith("@test.elfis.local")


def test_mock_mailer_failure_mode():
    mailer = MockMailerProvider()
    mailer.fail_next = True
    mailer.fail_mode = "temporary"
    try:
        mailer.send(to="x@test.elfis.local", subject="x", body="y")
        assert False, "should raise"
    except RuntimeError:
        pass
    assert mailer.outbox[-1].status == "failed"
