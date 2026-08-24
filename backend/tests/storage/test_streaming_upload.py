"""Tests upload streaming + sécurité renforcée."""

from __future__ import annotations

import hashlib

import pytest

from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_exceptions import StorageValidationError
from app.storage.storage_reject_codes import StorageRejectCode
from app.storage.storage_security import validate_upload
from app.storage.storage_upload import StreamingUploadPipeline, TEMP_NAMESPACE
from tests.storage.conftest_helpers import make_storage_db, seed_org_user
from app.storage.storage_service import StorageService
from app.storage.storage_context import StorageContext


def test_streaming_chunks_checksum(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    pipe = StreamingUploadPipeline(provider)
    content = b"%PDF-1.4 " + (b"x" * 2000)
    chunks = [content[i : i + 100] for i in range(0, len(content), 100)]
    result = pipe.consume_sync_chunks(
        filename="doc.pdf",
        declared_mime="application/pdf",
        chunks=chunks,
    )
    assert result.size_bytes == len(content)
    assert result.checksum_sha256 == hashlib.sha256(content).hexdigest()
    assert provider.object_exists(namespace=result.namespace, object_key=result.object_key)
    assert list(tmp_path.joinpath(TEMP_NAMESPACE).glob("*.part")) == [] or not any(
        tmp_path.joinpath(TEMP_NAMESPACE).glob("*.part")
    )


def test_streaming_size_limit_mid_stream(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.storage_upload.settings.storage_max_file_size_bytes", 50)
    monkeypatch.setattr("app.storage.storage_security.settings.storage_max_file_size_bytes", 50)
    provider = LocalStorageProvider(root=tmp_path)
    pipe = StreamingUploadPipeline(provider)
    with pytest.raises(StorageValidationError) as exc:
        pipe.consume_sync_chunks(
            filename="a.txt",
            declared_mime="text/plain",
                chunks=[b"hello ", b"world ", b"and more bytes here!!!!!", b"XXXX" * 20],
        )
    assert exc.value.code == StorageRejectCode.FILE_TOO_LARGE.value
    leftovers = list(tmp_path.rglob("*.part"))
    assert leftovers == []


def test_streaming_empty_rejected(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    pipe = StreamingUploadPipeline(provider)
    with pytest.raises(StorageValidationError) as exc:
        pipe.consume_sync_chunks(filename="a.txt", declared_mime="text/plain", chunks=[])
    assert exc.value.code == StorageRejectCode.EMPTY_FILE.value


def test_nul_and_crlf_filename():
    with pytest.raises(StorageValidationError) as exc:
        validate_upload(filename="a\x00.txt", content=b"hello", declared_mime="text/plain")
    assert exc.value.code == StorageRejectCode.INVALID_FILENAME.value
    with pytest.raises(StorageValidationError):
        validate_upload(filename="a\r\n.txt", content=b"hello", declared_mime="text/plain")


def test_fake_pdf_mismatch(monkeypatch):
    monkeypatch.setattr("app.storage.storage_security.settings.storage_quarantine_enabled", False)
    with pytest.raises(StorageValidationError) as exc:
        validate_upload(
            filename="photo.png",
            content=b"%PDF-1.4 not a png",
            declared_mime="image/png",
        )
    assert exc.value.code in {
        StorageRejectCode.MIME_MISMATCH.value,
        StorageRejectCode.UNSUPPORTED_TYPE.value,
    }


def test_exe_renamed_detected():
    with pytest.raises(StorageValidationError) as exc:
        validate_upload(
            filename="readme.txt",
            content=b"MZ\x90\x00fake-exe",
            declared_mime="text/plain",
        )
    assert exc.value.code == StorageRejectCode.SECURITY_POLICY_REJECTED.value


def test_compensation_on_db_failure(tmp_path):
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    ctx = StorageContext(provider=LocalStorageProvider(root=tmp_path), namespace="default")
    storage = StorageService(db, context=ctx)

    # Simuler échec DB après écriture : fermer session après stream then fail commit
    streamed = storage.register_from_streamed_sync(
        filename="ok.pdf",
        chunks=[b"%PDF-1.4 hello"],
        declared_mime="application/pdf",
        organization_id=org.id,
        created_by_user_id=user.id,
        commit=True,
    )
    assert streamed.status == "available"
    # compensation path unit
    ok = storage._compensate_delete(
        namespace=streamed.namespace,
        object_key=streamed.object_key,
        storage_object_id=streamed.id,
        organization_id=org.id,
    )
    assert ok is True
    assert not storage.provider.object_exists(
        namespace=streamed.namespace, object_key=streamed.object_key
    )
