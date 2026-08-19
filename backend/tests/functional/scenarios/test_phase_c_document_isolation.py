"""Phase C — Isolation documents (SEC-002/003, TENANT)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.accounting.accounting_schemas import AccountingPipelineRequest
from app.accounting.accounting_service import AccountingService
from app.ai.ai_models import ElfisDocumentAnalysis
from tests.functional.fixtures.generate_documents import ensure_document_fixtures
from tests.functional.helpers.phase_c import assert_safe_document_body, doc_id_from_archive


def test_sec_002_cross_tenant_document(api, mock_vault_storage):
    files = ensure_document_fixtures()
    api.login_user("active")
    body = api.upload_document(files["invoice_supplier_valid.pdf"], expect=(200, 201))
    doc_id = doc_id_from_archive(body)

    api.login_user("other_tenant")
    for path in (
        f"/api/vault/documents/{doc_id}",
        f"/api/documents/{doc_id}/text-extraction",
        f"/api/ai/documents/{doc_id}/analyze",
    ):
        r = api.client.get(path, headers=api._headers())
        assert r.status_code in (403, 404, 405)
        if r.headers.get("content-type", "").startswith("application/json"):
            assert_safe_document_body(r.json())


def test_sec_003_cross_tenant_proposal(api, functional_db):
    Session = functional_db["Session"]
    org_a = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        db.add(
            ElfisDocumentAnalysis(
                id=str(uuid4()),
                analysis_id=str(uuid4()),
                organization_id=org_a,
                vault_document_id="vd-iso-prop",
                document_version=1,
                status="completed",
                document_type="supplier_invoice",
                confidence=0.95,
                extraction={
                    "compatible_extraction": {
                        "supplier": "Iso SA",
                        "invoice_number": "ISO-1",
                        "invoice_date": "2026-07-01",
                        "amount_ht": 100,
                        "amount_tva": 20,
                        "amount_ttc": 120,
                        "vat_rate": 20,
                        "currency": "EUR",
                        "document_type": "supplier_invoice",
                    }
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        # Need vault doc for FK? may not be FK enforced on sqlite
        from app.models_vault import VaultDocument

        db.add(
            VaultDocument(
                id="vd-iso-prop",
                organization_id=org_a,
                document_type="supplier_invoice",
                original_filename="iso.pdf",
                storage_path="o/iso.pdf",
                mime_type="application/pdf",
                file_size=10,
                checksum_sha256="iso",
                archive_status="archived",
                version=1,
            )
        )
        db.commit()
        result = AccountingService(db).create_proposal(
            AccountingPipelineRequest(organization_id=org_a, vault_document_id="vd-iso-prop")
        )
        db.commit()
        proposal_id = result.proposal_id
    finally:
        db.close()

    api.login_user("other_tenant")
    r = api.client.get(f"/api/accounting/proposals/{proposal_id}", headers=api._headers())
    assert r.status_code in (403, 404)
    r2 = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json={"comment": "cross"},
    )
    assert r2.status_code in (401, 403, 404)
