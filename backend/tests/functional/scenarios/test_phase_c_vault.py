"""Phase C — Vault (VAULT-001 … VAULT-004)."""

from __future__ import annotations

from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.services.vault.checksum_service import calculate_sha256
from tests.document_intelligence import make_text_pdf
from tests.functional.fixtures.generate_documents import ensure_document_fixtures
from tests.functional.helpers.phase_c import assert_safe_document_body, doc_id_from_archive


def test_vault_001_002_archive_unique_hash(api, functional_db, mock_vault_storage):
    files = ensure_document_fixtures()
    api.login_user("active")
    content = files["invoice_text_pdf.pdf"].read_bytes()
    body = api.upload_document(content, filename="invoice_text_pdf.pdf", expect=(200, 201))
    doc_id = doc_id_from_archive(body)
    assert body.get("checksum_sha256") == calculate_sha256(content)
    assert len(mock_vault_storage.objects) == 1

    Session = functional_db["Session"]
    db = Session()
    try:
        ev = (
            db.query(ElfisEvent)
            .filter(
                ElfisEvent.event_name == EventNames.VAULT_DOCUMENT_ARCHIVED,
                ElfisEvent.organization_id == api.org_id,
            )
            .first()
        )
        assert ev is not None
        assert doc_id in str(ev.payload or {})
    finally:
        db.close()


def test_vault_003_duplicate_policy_409(api, mock_vault_storage):
    """Politique Vault route archive : doublon = 409 (pas de reuse silencieux)."""
    api.login_user("active")
    content = make_text_pdf("DUPLICATE-HASH-PHASE-C")
    r1 = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("dup1.pdf", content, "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    assert r1.status_code in (200, 201)
    r2 = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("dup2.pdf", content, "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    assert r2.status_code == 409
    body = r2.json()
    assert_safe_document_body(body)
    assert body.get("existing_document_id") or "déjà" in str(body).lower() or "deja" in str(body).lower()
    # Pas de second objet physique
    assert len(mock_vault_storage.objects) == 1


def test_vault_004_isolation(api, functional_db, mock_vault_storage):
    files = ensure_document_fixtures()
    api.login_user("active")
    body = api.upload_document(files["invoice_supplier_valid.pdf"], expect=(200, 201))
    doc_id = doc_id_from_archive(body)

    api.login_user("other_tenant")
    r = api.client.get(f"/api/vault/documents/{doc_id}", headers=api._headers())
    assert r.status_code in (403, 404)
    assert_safe_document_body(r.json())
    blob = str(r.json()).lower()
    assert "fournisseur fictif" not in blob
