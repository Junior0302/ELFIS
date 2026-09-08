"""Aucun contenu fichier / nom métier dans les logs antivirus."""

from __future__ import annotations

import logging

from app.security.antivirus import require_clean_user_upload
from tests.antivirus.conftest import EICAR_TEST, install_fake_clamd


def test_logs_do_not_contain_file_bytes(monkeypatch, antivirus_enabled, caplog):
    install_fake_clamd(monkeypatch, response=b"stream: Eicar-Test-File FOUND\n")
    secret = b"CONFIDENTIAL_INVOICE_PAYLOAD_DO_NOT_LOG"
    with caplog.at_level(logging.INFO, logger="app.security.antivirus"):
        try:
            require_clean_user_upload(
                data=secret + EICAR_TEST,
                upload_type="document_registry",
            )
        except Exception:
            pass
    joined = " ".join(r.getMessage() for r in caplog.records)
    extras = " ".join(str(getattr(r, "filename", "")) for r in caplog.records)
    blob = joined + extras + str(caplog.text)
    assert "CONFIDENTIAL_INVOICE_PAYLOAD_DO_NOT_LOG" not in blob
    assert EICAR_TEST.decode("ascii") not in blob
    assert "secret@example.com" not in blob
