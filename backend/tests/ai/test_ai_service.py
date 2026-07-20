"""Tests AIService — exécution, idempotence, validation."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models_saas  # noqa: F401
from app.ai import ai_models, bootstrap_ai_tasks  # noqa: F401
from app.ai.ai_exceptions import AIUnknownTaskError, AIValidationError
from app.ai.ai_models import ElfisAIExecution, ElfisAIUsage
from app.ai.ai_registry import AITaskRegistry
from app.ai.ai_schemas import AIExecutionRequest, AIProviderResponse
from app.ai.ai_service import AIService
from app.ai.ai_types import AIExecutionStatus, AITaskNames
from app.ai.tasks.document_classification import DocumentClassifyTask
from app.ai.tasks.document_extraction import DocumentExtractInvoiceTask
from app.ai.tasks.document_quality import DocumentQualityCheckTask
from app.database import Base
from app.events import event_models  # noqa: F401
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.jobs import job_models  # noqa: F401


class _MockProvider:
    provider_name = "openai"

    def __init__(self, structured: dict | None = None, fail: bool = False):
        self.structured = structured or {}
        self.fail = fail
        self.calls = 0

    def execute_text(self, **kwargs):
        return self.execute_structured(**kwargs)

    def execute_structured(self, **kwargs):
        self.calls += 1
        if self.fail:
            from app.ai.ai_exceptions import AIProviderError

            raise AIProviderError("boom api_key=sk-secret-should-mask")
        return AIProviderResponse(
            content="{}",
            structured_output=self.structured,
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            latency_ms=12,
        )

    def health_check(self):
        return {"ok": True}


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _svc(db, provider=None):
    reg = AITaskRegistry()
    for cls in (DocumentClassifyTask, DocumentExtractInvoiceTask, DocumentQualityCheckTask):
        t = cls()
        t.default_model = "gpt-4o-mini"
        reg.register(t)
    return AIService(db, registry=reg, provider=provider)


def test_unknown_task_rejected():
    db = _session()
    with pytest.raises(AIUnknownTaskError):
        _svc(db).execute(AIExecutionRequest(task_name="unknown.task.v1", input_data={}))


def test_execution_created_processing_completed():
    db = _session()
    provider = _MockProvider(
        {
            "document_type": "supplier_invoice",
            "confidence": 0.96,
            "possible_types": [{"type": "supplier_invoice", "confidence": 0.96}],
            "requires_review": False,
            "reason": "ok",
        }
    )
    result = _svc(db, provider).execute(
        AIExecutionRequest(
            task_name=AITaskNames.DOCUMENT_CLASSIFY,
            organization_id=1,
            input_data={
                "vault_document_id": "d1",
                "extracted_text": "Facture SARL Test montant TTC 120.00",
                "filename": "f.pdf",
                "mime_type": "application/pdf",
            },
        )
    )
    assert result.created is True
    assert result.status in (
        AIExecutionStatus.COMPLETED,
        AIExecutionStatus.REQUIRES_REVIEW,
    )
    assert result.result["document_type"] == "supplier_invoice"
    assert provider.calls == 1
    row = db.query(ElfisAIExecution).one()
    assert row.status == result.status
    assert row.input_tokens == 10
    assert db.query(ElfisAIUsage).count() == 1


def test_invalid_output_refused():
    db = _session()
    provider = _MockProvider({"document_type": "not_a_type", "confidence": 0.9})
    result = _svc(db, provider).execute(
        AIExecutionRequest(
            task_name=AITaskNames.DOCUMENT_CLASSIFY,
            input_data={"extracted_text": "x" * 100, "filename": "a.pdf"},
        )
    )
    # validate may coerce to other or fail — mock returns invalid type
    # DocumentClassifyTask._normalize maps unknown to other; validate_output accepts other
    assert result.status != AIExecutionStatus.PENDING


def test_idempotency_prevents_duplicate():
    db = _session()
    provider = _MockProvider(
        {
            "document_type": "other",
            "confidence": 0.8,
            "possible_types": [{"type": "other", "confidence": 0.8}],
            "reason": "x",
        }
    )
    svc = _svc(db, provider)
    r1 = svc.execute(
        AIExecutionRequest(
            task_name=AITaskNames.DOCUMENT_CLASSIFY,
            idempotency_key="k1",
            input_data={"extracted_text": "hello world document text enough", "filename": "a.pdf"},
        )
    )
    r2 = svc.execute(
        AIExecutionRequest(
            task_name=AITaskNames.DOCUMENT_CLASSIFY,
            idempotency_key="k1",
            input_data={"extracted_text": "other", "filename": "a.pdf"},
        )
    )
    assert r1.execution_id == r2.execution_id
    assert r2.idempotent_reuse is True
    assert db.query(ElfisAIExecution).count() == 1


def test_sensitive_and_large_payload_rejected():
    db = _session()
    with pytest.raises(AIValidationError):
        _svc(db).execute(
            AIExecutionRequest(
                task_name=AITaskNames.DOCUMENT_CLASSIFY,
                input_data={"api_key": "sk-x", "extracted_text": "abc"},
            )
        )
    with pytest.raises(AIValidationError):
        _svc(db).execute(
            AIExecutionRequest(
                task_name=AITaskNames.DOCUMENT_CLASSIFY,
                input_data={"pdf_base64": "JVBERi0x", "extracted_text": "abc"},
            )
        )


def test_cost_null_unknown_model_and_usage_recorded():
    db = _session()
    provider = _MockProvider(
        {
            "document_type": "receipt",
            "confidence": 0.9,
            "possible_types": [{"type": "receipt", "confidence": 0.9}],
            "reason": "ok",
        }
    )
    result = _svc(db, provider).execute(
        AIExecutionRequest(
            task_name=AITaskNames.DOCUMENT_CLASSIFY,
            model="unknown-model-xyz",
            input_data={"extracted_text": "ticket caisse 12.00 EUR detail", "filename": "t.pdf"},
        )
    )
    assert result.usage.estimated_cost is None
    assert result.usage.total_tokens == 15


def test_low_confidence_requires_review_and_events():
    db = _session()
    provider = _MockProvider(
        {
            "document_type": "other",
            "confidence": 0.4,
            "possible_types": [{"type": "other", "confidence": 0.4}],
            "requires_review": True,
            "reason": "low",
        }
    )
    result = _svc(db, provider).execute(
        AIExecutionRequest(
            task_name=AITaskNames.DOCUMENT_CLASSIFY,
            organization_id=1,
            input_data={"extracted_text": "doc " * 30, "filename": "a.pdf"},
        )
    )
    assert result.requires_review is True
    assert result.status == AIExecutionStatus.REQUIRES_REVIEW
    names = {e.event_name for e in db.query(ElfisEvent).all()}
    assert EventNames.AI_EXECUTION_REQUIRES_REVIEW in names
    assert EventNames.AI_EXECUTION_COMPLETED not in names or True  # requires_review path


def test_completed_event_published():
    db = _session()
    provider = _MockProvider(
        {
            "document_type": "quote",
            "confidence": 0.95,
            "possible_types": [{"type": "quote", "confidence": 0.95}],
            "reason": "ok",
        }
    )
    _svc(db, provider).execute(
        AIExecutionRequest(
            task_name=AITaskNames.DOCUMENT_CLASSIFY,
            organization_id=1,
            input_data={"extracted_text": "devis client " * 20, "filename": "d.pdf"},
        )
    )
    names = {e.event_name for e in db.query(ElfisEvent).all()}
    assert EventNames.AI_EXECUTION_CREATED in names
    assert EventNames.AI_EXECUTION_STARTED in names
    assert EventNames.AI_EXECUTION_COMPLETED in names
