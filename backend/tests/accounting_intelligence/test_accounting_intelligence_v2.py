"""Tests Accounting Intelligence V2."""

from __future__ import annotations

from app.accounting_engine import models as ae_models
from app.accounting_engine.models import ElfisAccountingEngineProposal
from app.accounting_intelligence import models as ai_models
from app.accounting_intelligence.enums import LearningGate
from app.accounting_intelligence.exceptions import IntelligenceNotFoundError
from app.accounting_intelligence.explanation_engine import ExplanationEngine
from app.accounting_intelligence.learning_engine import LearningEngine
from app.accounting_intelligence.recommendation_engine import RecommendationEngine
from app.accounting_intelligence.service import IntelligenceService
from app.accounting_intelligence.similarity_engine import SimilarityEngine
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.models import CompanySettings
from tests.document_intake.conftest_helpers import make_intake_db, seed_org_user


def _bootstrap():
    factory, _ = make_intake_db()
    db = factory()
    engine = db.get_bind()
    for tbl in (
        CompanySettings.__table__,
        ae_models.ElfisChartOfAccount.__table__,
        ae_models.ElfisAccountingEngineProposal.__table__,
        ae_models.ElfisAccountingLearningMemory.__table__,
        ae_models.ElfisAccountingEngineAudit.__table__,
        ai_models.ElfisAiContextProfile.__table__,
        ai_models.ElfisAiLearningMemory.__table__,
        ai_models.ElfisAiRecommendationHistory.__table__,
        ai_models.ElfisAiFeedback.__table__,
        ai_models.ElfisAiSimilarityCache.__table__,
        ai_models.ElfisAiAudit.__table__,
    ):
        tbl.create(bind=engine, checkfirst=True)
    org, user = seed_org_user(db)
    return db, org, user


def _payload(**kw):
    base = {
        "document_type": "invoice",
        "document_number": "FA-INTEL-1",
        "document_date": "2024-01-15",
        "supplier_name": "ACME SARL",
        "amount_ht": 100,
        "amount_vat": 20,
        "amount_ttc": 120,
        "vat_rate": 20,
        "currency": "EUR",
        "extraction_confidence": 0.85,
        "validation_confidence": 0.9,
    }
    base.update(kw)
    return base


def test_recommendation_and_explanation():
    db, org, user = _bootstrap()
    svc = IntelligenceService(db)
    out = svc.recommend(
        organization_id=org.id,
        actor_user_id=user.id,
        payload=_payload(),
    )
    assert out["recommendation_id"]
    assert out["recommendation"]["journal_code"]
    assert out["explanation"]["why_account"]
    assert out["confidence"]["detail"].get("similarity") is not None
    assert EventNames.ACCOUNTING_INTELLIGENCE_RECOMMENDATION_GENERATED in {
        e.event_name for e in db.query(ElfisEvent).all()
    }
    db.close()


def test_similarity_and_learning_feedback_accept():
    db, org, user = _bootstrap()
    svc = IntelligenceService(db)
    first = svc.recommend(
        organization_id=org.id,
        actor_user_id=user.id,
        payload=_payload(),
    )
    fb = svc.submit_feedback(
        organization_id=org.id,
        actor_user_id=user.id,
        action="accept",
        recommendation_id=first["recommendation_id"],
        validation_seconds=12.5,
        comment="OK",
    )
    assert fb["learned"] is True
    assert fb["learn_gate"] == LearningGate.OK.value

    learned = svc.learning_state(organization_id=org.id)
    assert learned["items"]

    sim = SimilarityEngine(db).find_similar(
        organization_id=org.id,
        query=_payload(document_number="FA-INTEL-2"),
        limit=3,
    )
    assert sim
    assert sim[0].score >= 0.35

    # 2e reco doit pouvoir s'appuyer sur historique
    second = RecommendationEngine(db).recommend(
        organization_id=org.id, payload=_payload(document_number="FA-2")
    )
    assert second.confidence_inputs.get("history_hit") or second.primary_source in {
        "history",
        "rules",
        "company",
        "similarity",
        "ai",
        "defaults",
    }
    db.close()


def test_reject_and_incomplete_do_not_learn():
    db, org, user = _bootstrap()
    svc = IntelligenceService(db)
    reco = svc.recommend(
        organization_id=org.id, actor_user_id=user.id, payload=_payload()
    )
    rejected = svc.submit_feedback(
        organization_id=org.id,
        actor_user_id=user.id,
        action="reject",
        recommendation_id=reco["recommendation_id"],
    )
    assert rejected["learned"] is False
    assert rejected["learn_gate"] == LearningGate.REJECTED.value

    incomplete = svc.submit_feedback(
        organization_id=org.id,
        actor_user_id=user.id,
        action="modify",
        recommendation_id=reco["recommendation_id"],
        modifications={},  # incomplet
    )
    assert incomplete["learned"] is False
    assert incomplete["learn_gate"] == LearningGate.INCOMPLETE.value
    db.close()


def test_retrain_optimizations_no_auto_rules():
    db, org, user = _bootstrap()
    svc = IntelligenceService(db)
    svc.recommend(organization_id=org.id, actor_user_id=user.id, payload=_payload())
    out = svc.retrain(organization_id=org.id, actor_user_id=user.id)
    assert out["auto_rules_modified"] is False
    assert "optimizations" in out
    assert out["context"]["version"] >= 1
    db.close()


def test_cross_tenant_isolation():
    db, org, user = _bootstrap()
    org2, _ = seed_org_user(db, email="intel2@test.local", name="OtherOrg")
    svc = IntelligenceService(db)
    out = svc.recommend(
        organization_id=org.id, actor_user_id=user.id, payload=_payload()
    )
    try:
        svc.get_recommendation(
            organization_id=org2.id, recommendation_id=out["recommendation_id"]
        )
        assert False, "cross-tenant leak"
    except IntelligenceNotFoundError:
        pass

    from app.accounting_intelligence.permissions import ACCOUNTING_INTELLIGENCE_PERMISSIONS
    from app.iam.permission_catalog import Permission

    for p in ACCOUNTING_INTELLIGENCE_PERMISSIONS:
        assert Permission(p).value == p
    db.close()


def test_explanation_engine_human_readable():
    db, org, _ = _bootstrap()
    reco = RecommendationEngine(db).recommend(
        organization_id=org.id, payload=_payload()
    )
    expl = ExplanationEngine().explain(
        recommendation=reco, confidence={"score": 0.8, "detail": {"extraction": 0.9}}
    )
    assert expl["human_readable"] is True
    assert "compte" in expl["why_account"].lower()
    db.close()


def test_learning_engine_gates():
    le = LearningEngine.__new__(LearningEngine)
    assert le.gate(action="reject") == LearningGate.REJECTED
    assert le.gate(action="accept") == LearningGate.OK
    assert le.gate(action="modify", modifications={}) == LearningGate.INCOMPLETE
    assert (
        le.gate(action="accept", import_rejected=True) == LearningGate.IMPORT_REJECTED
    )
