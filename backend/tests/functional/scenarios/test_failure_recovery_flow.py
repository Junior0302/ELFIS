"""SCENARIO — Erreurs / retries / recovery mocks."""

from __future__ import annotations

from tests.functional.fixtures.mock_providers import MockAIProvider, MockStorageProvider


def test_ai_permanent_failure():
    ai = MockAIProvider()
    ai.mode = "permanent"
    try:
        ai.complete()
        assert False
    except RuntimeError as exc:
        assert "permanent" in str(exc)


def test_storage_upload_failure():
    storage = MockStorageProvider()
    storage.fail_upload = True
    try:
        storage.upload_object("k", b"data")
        assert False
    except RuntimeError:
        pass


def test_stripe_synthetic_events():
    from tests.functional.fixtures.mock_providers import MockStripeProvider

    stripe = MockStripeProvider()
    ev = stripe.build_event(
        "customer.subscription.updated",
        "sub_recette_1",
        status="past_due",
    )
    assert ev["livemode"] is False
    assert ev["type"] == "customer.subscription.updated"
