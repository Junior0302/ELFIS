"""Tests taxonomie + classifiers + scoring."""

from __future__ import annotations

import asyncio

from app.document_processing.classification.classifiers.composite import CompositeDocumentClassifier
from app.document_processing.classification.classifiers.filename import FilenameRuleClassifier
from app.document_processing.classification.classifiers.base import ClassificationContext
from app.document_processing.classification.scoring import ClassificationScoringPolicy
from app.document_processing.classification.taxonomy import get_document_type_registry
from app.storage.storage_models import ElfisStorageObject
from tests.document_classification.conftest_helpers import make_classification_db, seed_document, seed_org_user


def test_taxonomy_known_and_aliases():
    reg = get_document_type_registry()
    assert reg.is_known("supplier_invoice")
    assert reg.resolve_key("devis") == "quote"
    assert reg.resolve_key("avoir") == "credit_note"
    assert reg.get("unknown")
    assert any(t.sensitive for t in reg.list_types())


def test_scoring_thresholds():
    p = ClassificationScoringPolicy(confirm_threshold=0.9, review_threshold=0.55, auto_confirm=False)
    assert p.requires_review(0.8)
    assert not p.is_auto_confirmable(0.95)
    p2 = ClassificationScoringPolicy(confirm_threshold=0.9, review_threshold=0.55, auto_confirm=True)
    assert p2.is_auto_confirmable(0.95)
    assert not p2.is_auto_confirmable(0.95, ambiguous=True)


def _ctx(db, doc, ver, obj=None):
    return ClassificationContext(
        db=db,
        document=doc,
        version=ver,
        storage_object=obj,
        links=[],
        organization_id=doc.organization_id,
    )


def test_filename_invoice_ambiguous(tmp_path):
    factory, _ = make_classification_db()
    db = factory()
    org, user = seed_org_user(db)
    from app.storage.storage_models import ElfisDocumentVersion

    doc = seed_document(db, tmp_path, org, user, filename="facture-2024.pdf", content=b"%PDF-1.4")
    ver = db.get(ElfisDocumentVersion, doc.current_version_id)
    res = asyncio.run(FilenameRuleClassifier().classify(_ctx(db, doc, ver)))
    assert res.predicted_type == "invoice"
    assert any(a.type_key in ("supplier_invoice", "customer_invoice") for a in res.alternatives)
    assert not any("@" in (e.detail or "") for e in res.evidence)
    assert not any("facture-2024" in (e.code or "") for e in res.evidence)


def test_filename_quote_and_contract(tmp_path):
    factory, _ = make_classification_db()
    db = factory()
    org, user = seed_org_user(db)
    from app.storage.storage_models import ElfisDocumentVersion

    for name, expected in (("devis-client.pdf", "quote"), ("contrat-service.pdf", "contract"), ("avoir-janvier.pdf", "credit_note"), ("releve-banque.pdf", "bank_statement")):
        doc = seed_document(db, tmp_path, org, user, filename=name, content=b"%PDF-1.4 x")
        ver = db.get(ElfisDocumentVersion, doc.current_version_id)
        res = asyncio.run(FilenameRuleClassifier().classify(_ctx(db, doc, ver)))
        assert res.predicted_type == expected, (name, res.predicted_type)


def test_filename_with_email_no_leak(tmp_path):
    factory, _ = make_classification_db()
    db = factory()
    org, user = seed_org_user(db)
    from app.storage.storage_models import ElfisDocumentVersion

    # PII dans le nom sans double extension (rejeté par storage security)
    doc = seed_document(
        db, tmp_path, org, user, filename="facture_john_doe_at_corp_example.pdf", content=b"%PDF"
    )
    ver = db.get(ElfisDocumentVersion, doc.current_version_id)
    # Simule un filename contenant un email côté classifier uniquement
    ver.original_filename = "facture_john.doe@corp.example.pdf"
    db.commit()
    res = asyncio.run(FilenameRuleClassifier().classify(_ctx(db, doc, ver)))
    blob = str([(e.code, e.detail) for e in res.evidence])
    assert "john.doe@corp.example" not in blob
    assert "corp.example" not in blob or "keyword_match" in blob


def test_composite_pipeline_result(tmp_path):
    factory, _ = make_classification_db()
    db = factory()
    org, user = seed_org_user(db)
    from app.storage.storage_models import ElfisDocumentVersion, ElfisStorageObject

    doc = seed_document(db, tmp_path, org, user, filename="devis.pdf", content=b"%PDF-1.4")
    ver = db.get(ElfisDocumentVersion, doc.current_version_id)
    obj = db.get(ElfisStorageObject, ver.storage_object_id) if ver else None
    res = asyncio.run(CompositeDocumentClassifier().classify(_ctx(db, doc, ver, obj)))
    assert res.predicted_type == "quote"
    assert 0 <= res.confidence_score <= 1
    assert res.classifier_key == "composite_deterministic"
