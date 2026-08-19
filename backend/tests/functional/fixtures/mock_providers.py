"""Mocks de recette — aucun appel réseau réel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MockMailMessage:
    to: str
    subject: str
    body: str
    html: str | None = None
    attachments: list[dict[str, Any]] = field(default_factory=list)
    status: str = "sent"
    attempts: int = 1
    meta: dict[str, Any] = field(default_factory=dict)


class MockMailerProvider:
    """Outbox locale en mémoire."""

    def __init__(self) -> None:
        self.outbox: list[MockMailMessage] = []
        self.fail_next = False
        self.fail_mode: str | None = None  # temporary|permanent

    def reset(self) -> None:
        self.outbox.clear()
        self.fail_next = False
        self.fail_mode = None

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        **meta: Any,
    ) -> MockMailMessage:
        if self.fail_next:
            self.fail_next = False
            msg = MockMailMessage(
                to=to,
                subject=subject,
                body=body,
                html=html,
                attachments=attachments or [],
                status="failed",
                attempts=1,
                meta={"error": self.fail_mode or "mock_failure", **meta},
            )
            self.outbox.append(msg)
            raise RuntimeError(f"mock_mailer_{self.fail_mode or 'error'}")
        msg = MockMailMessage(
            to=to,
            subject=subject,
            body=body,
            html=html,
            attachments=attachments or [],
            status="sent",
            meta=dict(meta),
        )
        self.outbox.append(msg)
        return msg


@dataclass
class MockAIResponse:
    content: dict[str, Any]
    confidence: float = 0.95
    tokens: int = 100


class MockAIProvider:
    def __init__(self) -> None:
        self.mode = "success"  # success|temporary|permanent|timeout|low_confidence|incomplete
        self.calls = 0

    def reset(self) -> None:
        self.mode = "success"
        self.calls = 0

    def complete(self, *args: Any, **kwargs: Any) -> MockAIResponse:
        self.calls += 1
        if self.mode == "temporary" and self.calls < 2:
            raise TimeoutError("mock_ai_temporary")
        if self.mode == "permanent":
            raise RuntimeError("mock_ai_permanent")
        if self.mode == "timeout":
            raise TimeoutError("mock_ai_timeout")
        confidence = 0.4 if self.mode == "low_confidence" else 0.95
        content: dict[str, Any] = {
            "document_type": "supplier_invoice",
            "invoice_number": "FAC-RECETTE-001",
            "currency": "EUR",
            "amount_ht": 100.0,
            "amount_vat": 20.0,
            "amount_ttc": 120.0,
            "supplier_name": "Fournisseur Fictif SA",
            "balanced": True,
        }
        if self.mode == "incomplete":
            content.pop("amount_vat", None)
            content["balanced"] = False
        return MockAIResponse(content=content, confidence=confidence)


class MockOCRProvider:
    def __init__(self) -> None:
        self.mode = "success"

    def extract(self, content: bytes) -> dict[str, Any]:
        if self.mode == "unavailable":
            raise RuntimeError("ocr_unavailable")
        if self.mode == "empty":
            return {"text": "", "confidence": 0.0}
        return {"text": "Facture OCR mock HT 100 TVA 20 TTC 120", "confidence": 0.88}


class MockStripeProvider:
    """Événements webhook synthétiques — pas d'appel réseau."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def build_event(self, event_type: str, object_id: str, **data: Any) -> dict[str, Any]:
        event = {
            "id": f"evt_recette_{object_id}",
            "type": event_type,
            "data": {"object": {"id": object_id, **data}},
            "livemode": False,
        }
        self.events.append(event)
        return event


class MockStorageProvider:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail_upload = False

    def upload_object(self, key: str, content: bytes, **kwargs: Any) -> str:
        if self.fail_upload:
            raise RuntimeError("mock_storage_upload_failed")
        self.objects[key] = content
        return key

    def delete_object(self, key: str) -> None:
        self.objects.pop(key, None)

    def create_signed_url(self, key: str, ttl: int = 300) -> str:
        return f"https://mock-storage.test/{key}?ttl={ttl}&sig=recette"


# Singleton pratique pour les tests
mailer_outbox = MockMailerProvider()
ai_mock = MockAIProvider()
ocr_mock = MockOCRProvider()
stripe_mock = MockStripeProvider()
storage_mock = MockStorageProvider()
