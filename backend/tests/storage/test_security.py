"""Tests validation sécurité fichiers."""

from __future__ import annotations

import pytest

from app.storage.storage_exceptions import StorageValidationError
from app.storage.storage_reject_codes import StorageRejectCode
from app.storage.storage_security import validate_upload


def test_valid_pdf(monkeypatch):
    monkeypatch.setattr("app.storage.storage_security.settings.storage_checksum_enabled", True)
    result = validate_upload(
        filename="facture.pdf",
        content=b"%PDF-1.4 content here",
        declared_mime="application/pdf",
    )
    assert result.quarantined is False
    assert result.checksum_sha256
    assert result.extension == ".pdf"


def test_empty_file_rejected():
    with pytest.raises(StorageValidationError) as exc:
        validate_upload(filename="a.txt", content=b"", declared_mime="text/plain")
    assert exc.value.code == StorageRejectCode.EMPTY_FILE.value


def test_too_large(monkeypatch):
    monkeypatch.setattr("app.storage.storage_security.settings.storage_max_file_size_bytes", 10)
    with pytest.raises(StorageValidationError) as exc:
        validate_upload(filename="a.txt", content=b"01234567890", declared_mime="text/plain")
    assert exc.value.code == StorageRejectCode.FILE_TOO_LARGE.value


def test_blocked_extension():
    with pytest.raises(StorageValidationError) as exc:
        validate_upload(filename="malware.exe", content=b"MZxxxx", declared_mime="application/octet-stream")
    assert exc.value.code == StorageRejectCode.BLOCKED_EXTENSION.value


def test_dangerous_filename():
    with pytest.raises(StorageValidationError) as exc:
        validate_upload(filename="../x.txt", content=b"hello", declared_mime="text/plain")
    assert exc.value.code == StorageRejectCode.INVALID_FILENAME.value


def test_double_extension():
    with pytest.raises(StorageValidationError) as exc:
        validate_upload(filename="doc.php.pdf", content=b"%PDF-1.4", declared_mime="application/pdf")
    assert exc.value.code == StorageRejectCode.BLOCKED_EXTENSION.value


def test_mime_not_allowed():
    with pytest.raises(StorageValidationError) as exc:
        validate_upload(
            filename="x.bin",
            content=b"\x00\x01\x02",
            declared_mime="application/x-msdownload",
        )
    assert exc.value.code == StorageRejectCode.UNSUPPORTED_TYPE.value
