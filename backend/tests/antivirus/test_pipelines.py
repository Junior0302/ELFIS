"""Pipelines upload — registry / vault / intake / legacy / logo / avatar."""

from __future__ import annotations

import pytest

from app.document_intake.enums import IntakeItemStatus
from app.document_intake.exceptions import DocumentIntakeValidationError
from app.document_intake.service import DocumentIntakeService
from app.security.antivirus import AntivirusError, AntivirusErrorCode
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_context import StorageContext
from app.storage.storage_exceptions import StorageValidationError
from app.storage.storage_service import StorageService
from app.storage.storage_upload import StreamingUploadPipeline
from tests.antivirus.conftest import EICAR_TEST, install_fake_clamd
from tests.document_intake.conftest_helpers import PDF_MINIMAL, make_intake_db, seed_org_user as seed_intake
from tests.storage.conftest_helpers import make_storage_db, seed_org_user
from tests.vault.test_vault_archive import MINIMAL_PDF, _mock_storage, _seed_org_user, _session


def _enable_prod(monkeypatch):
    for target in (
        "app.config.settings.app_env",
        "app.config.settings.elfis_environment",
        "app.security.antivirus.settings.app_env",
        "app.security.antivirus.settings.elfis_environment",
    ):
        monkeypatch.setattr(target, "production")


def test_registry_clean_stores_object(tmp_path, antivirus_enabled, monkeypatch):
    install_fake_clamd(monkeypatch, response=b"stream: OK\n")
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    provider = LocalStorageProvider(root=tmp_path)
    svc = StorageService(db, context=StorageContext(provider=provider, namespace="default"))
    obj = svc.register_from_streamed_sync(
        filename="note.txt",
        chunks=[b"hello clean registry"],
        declared_mime="text/plain",
        organization_id=org.id,
        created_by_user_id=user.id,
    )
    assert obj.scan_status == "clean"
    assert provider.object_exists(namespace=obj.namespace, object_key=obj.object_key)


def test_registry_infected_no_put(tmp_path, antivirus_enabled, monkeypatch):
    install_fake_clamd(monkeypatch, response=b"stream: Eicar-Test-File FOUND\n")
    provider = LocalStorageProvider(root=tmp_path)
    original_put = provider.put_stream
    calls = {"n": 0}

    def _put(*args, **kwargs):
        calls["n"] += 1
        return original_put(*args, **kwargs)

    provider.put_stream = _put  # type: ignore[method-assign]
    pipe = StreamingUploadPipeline(provider)
    with pytest.raises(StorageValidationError) as exc:
        pipe.consume_sync_chunks(
            filename="eicar.txt",
            declared_mime="text/plain",
            chunks=[EICAR_TEST],
        )
    assert exc.value.code == AntivirusErrorCode.FILE_INFECTED
    assert calls["n"] == 0
    assert list(tmp_path.rglob("*.part")) == []
    assert list(tmp_path.rglob("eicar*")) == []


def test_vault_infected_no_put(antivirus_enabled, monkeypatch):
    install_fake_clamd(monkeypatch, response=b"stream: Eicar-Test-File FOUND\n")
    from app.schemas_vault import VaultArchiveFormMeta, VaultDocumentType
    from app.services.vault.exceptions import VaultAntivirusError
    from app.services.vault.vault_service import archive_document

    db = _session()
    user_id, org_id = _seed_org_user(db)
    storage = _mock_storage()
    with pytest.raises(VaultAntivirusError) as exc:
        archive_document(
            db,
            user_id=user_id,
            meta=VaultArchiveFormMeta(
                tenant_id=org_id,
                document_type=VaultDocumentType.customer_invoice,
            ),
            filename="eicar.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.4\n" + EICAR_TEST + b"\n%%EOF\n",
            storage=storage,
        )
    assert exc.value.code == AntivirusErrorCode.FILE_INFECTED
    storage._client.upload_object.assert_not_called()


def test_vault_clean_stores(antivirus_enabled, monkeypatch):
    install_fake_clamd(monkeypatch, response=b"stream: OK\n")
    from app.schemas_vault import VaultArchiveFormMeta, VaultDocumentType
    from app.services.vault.vault_service import archive_document

    db = _session()
    user_id, org_id = _seed_org_user(db)
    storage = _mock_storage()
    doc = archive_document(
        db,
        user_id=user_id,
        meta=VaultArchiveFormMeta(
            tenant_id=org_id,
            document_type=VaultDocumentType.customer_invoice,
            document_number="F-1",
        ),
        filename="ok.pdf",
        content_type="application/pdf",
        content=MINIMAL_PDF,
        storage=storage,
    )
    storage._client.upload_object.assert_called_once()
    from app.models_vault import VaultDocument

    persisted = db.get(VaultDocument, doc.id)
    assert persisted is not None
    assert persisted.scan_status == "clean"
    assert persisted.content_origin == "user_upload"


def test_vault_new_generated_sets_elfis_origin(antivirus_enabled, monkeypatch):
    from app.schemas_vault import VaultDocumentType
    from app.services.vault.vault_service import archive_or_reuse_pdf

    db = _session()
    user_id, org_id = _seed_org_user(db)
    storage = _mock_storage()
    doc, reused = archive_or_reuse_pdf(
        db,
        user_id=user_id,
        organization_id=org_id,
        document_type=VaultDocumentType.customer_invoice,
        document_number="FAC-GEN",
        filename="fac-gen.pdf",
        content=MINIMAL_PDF,
        storage=storage,
        skip_access_check=True,
    )
    assert reused is False
    assert doc.content_origin == "generated_by_elfis"
    assert doc.scan_engine == "elfis_generated"
    storage._client.upload_object.assert_called_once()


def test_intake_clean_ready_for_analysis(antivirus_enabled, monkeypatch):
    install_fake_clamd(monkeypatch, response=b"stream: OK\n")
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_intake(db)
    row = DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="invoice.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user.id,
        declared_mime="application/pdf",
    )
    assert row.scan_verdict == "clean"
    assert row.status == IntakeItemStatus.READY_FOR_ANALYSIS.value


def test_intake_non_clean_never_ready(antivirus_enabled, monkeypatch):
    install_fake_clamd(monkeypatch, response=b"stream: Eicar-Test-File FOUND\n")
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_intake(db)
    with pytest.raises(DocumentIntakeValidationError) as exc:
        DocumentIntakeService(db).ingest_bytes(
            organization_id=org.id,
            filename="eicar.pdf",
            content=PDF_MINIMAL,
            actor_user_id=user.id,
            declared_mime="application/pdf",
        )
    assert exc.value.code == AntivirusErrorCode.FILE_INFECTED
    from app.document_intake.models import ElfisDocumentIntakeItem

    assert db.query(ElfisDocumentIntakeItem).count() == 0


def test_legacy_invoice_infected_refused(antivirus_enabled, monkeypatch):
    install_fake_clamd(monkeypatch, response=b"stream: Eicar-Test-File FOUND\n")
    from app.security.antivirus import require_clean_user_upload

    with pytest.raises(AntivirusError) as exc:
        require_clean_user_upload(data=EICAR_TEST, upload_type="legacy_invoice")
    assert exc.value.code == AntivirusErrorCode.FILE_INFECTED


def test_svg_user_upload_rejected():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.database import get_db
    from app.deps import AuthContext, get_auth_context
    from app.routers.org import LOGO_TYPES, router as org_router

    assert "image/svg+xml" not in LOGO_TYPES
    assert ".svg" not in LOGO_TYPES.values()

    class _Db:
        def get(self, *_args, **_kwargs):
            return type("Org", (), {"id": 1, "logo": ""})()

    app = FastAPI()
    app.include_router(org_router, prefix="/api")
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        user=type("U", (), {"id": 1})(),
        organization_id=1,
        role="owner",
        permissions=["settings.manage"],
    )
    app.dependency_overrides[get_db] = lambda: _Db()
    client = TestClient(app)
    res = client.post(
        "/api/org/1/logo",
        files={"file": ("logo.svg", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/svg+xml")},
    )
    assert res.status_code == 400
    body = res.json()
    detail = body.get("detail") or {}
    if isinstance(detail, dict):
        assert detail.get("code") == "unsupported_file_type"
    assert "SVG" in str(body)


def test_logo_infected_refused(antivirus_enabled, monkeypatch):
    install_fake_clamd(monkeypatch, response=b"stream: Eicar-Test-File FOUND\n")
    from app.security.antivirus import require_clean_user_upload

    with pytest.raises(AntivirusError) as exc:
        require_clean_user_upload(data=b"\x89PNG\r\n\x1a\n" + EICAR_TEST, upload_type="org_logo")
    assert exc.value.code == AntivirusErrorCode.FILE_INFECTED


def test_avatar_infected_refused(antivirus_enabled, monkeypatch):
    install_fake_clamd(monkeypatch, response=b"stream: Eicar-Test-File FOUND\n")
    from app.security.antivirus import require_clean_user_upload

    with pytest.raises(AntivirusError) as exc:
        require_clean_user_upload(data=b"\xff\xd8\xff" + EICAR_TEST, upload_type="avatar")
    assert exc.value.code == AntivirusErrorCode.FILE_INFECTED


def test_production_disabled_upload_refused(monkeypatch, tmp_path):
    _enable_prod(monkeypatch)
    monkeypatch.setattr("app.config.settings.elfis_antivirus_enabled", False)
    monkeypatch.setattr("app.security.antivirus.settings.elfis_antivirus_enabled", False)
    provider = LocalStorageProvider(root=tmp_path)
    pipe = StreamingUploadPipeline(provider)
    with pytest.raises(StorageValidationError) as exc:
        pipe.consume_sync_chunks(
            filename="a.txt",
            declared_mime="text/plain",
            chunks=[b"hello"],
        )
    assert exc.value.code == AntivirusErrorCode.ANTIVIRUS_UNAVAILABLE
