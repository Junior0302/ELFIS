"""Politique fail-closed / disable explicite."""

from __future__ import annotations

import pytest

from app.security.antivirus import (
    AntivirusError,
    AntivirusErrorCode,
    AntivirusVerdict,
    require_clean_user_upload,
    scan_user_upload,
)
from tests.antivirus.conftest import install_fake_clamd


def test_disabled_in_test_is_explicit_skip(monkeypatch):
    monkeypatch.setattr("app.config.settings.elfis_antivirus_enabled", False)
    monkeypatch.setattr("app.security.antivirus.settings.elfis_antivirus_enabled", False)
    monkeypatch.setattr("app.security.antivirus.settings.app_env", "test")
    monkeypatch.setattr("app.security.antivirus.settings.elfis_environment", "test")
    monkeypatch.setattr("app.config.settings.app_env", "test")
    monkeypatch.setattr("app.config.settings.elfis_environment", "test")
    result = scan_user_upload(data=b"%PDF-1.4", upload_type="document_registry")
    assert result.verdict == AntivirusVerdict.CLEAN
    assert result.engine == "disabled"
    assert result.scanned is False
    assert result.details.get("reason") == "scanner_disabled_non_production"


def test_production_disabled_av_does_not_affect_ready_or_live(monkeypatch):
    import inspect

    from app.observability.health import live, ready

    monkeypatch.setattr("app.config.settings.elfis_antivirus_enabled", False)
    monkeypatch.setattr("app.config.settings.app_env", "production")
    monkeypatch.setattr("app.config.settings.elfis_environment", "production")
    assert live()["status"] == "ok"
    source = inspect.getsource(ready).lower()
    assert "antivirus" not in source
    assert "clamd" not in source
    assert "elfis_antivirus" not in source


def test_disabled_in_production_refuses(monkeypatch):
    monkeypatch.setattr("app.config.settings.elfis_antivirus_enabled", False)
    monkeypatch.setattr("app.security.antivirus.settings.elfis_antivirus_enabled", False)
    monkeypatch.setattr("app.config.settings.app_env", "production")
    monkeypatch.setattr("app.config.settings.elfis_environment", "production")
    monkeypatch.setattr("app.security.antivirus.settings.app_env", "production")
    monkeypatch.setattr("app.security.antivirus.settings.elfis_environment", "production")
    result = scan_user_upload(data=b"%PDF-1.4", upload_type="document_registry")
    assert result.verdict == AntivirusVerdict.UNAVAILABLE
    with pytest.raises(AntivirusError) as exc:
        require_clean_user_upload(data=b"%PDF-1.4", upload_type="document_registry")
    assert exc.value.code == AntivirusErrorCode.ANTIVIRUS_UNAVAILABLE
    assert exc.value.http_status == 503


def test_clean_accepted_when_enabled(monkeypatch, antivirus_enabled):
    install_fake_clamd(monkeypatch, response=b"stream: OK\n")
    result = require_clean_user_upload(data=b"%PDF-1.4 hello", upload_type="document_registry")
    assert result.verdict == AntivirusVerdict.CLEAN
    assert result.scanned is True


def test_infected_refused(monkeypatch, antivirus_enabled):
    install_fake_clamd(monkeypatch, response=b"stream: Eicar-Test-File FOUND\n")
    with pytest.raises(AntivirusError) as exc:
        require_clean_user_upload(data=b"X5O", upload_type="document_registry")
    assert exc.value.code == AntivirusErrorCode.FILE_INFECTED
    assert exc.value.http_status == 422


def test_unavailable_fail_closed(monkeypatch, antivirus_enabled):
    install_fake_clamd(monkeypatch, fail_mode="network")
    with pytest.raises(AntivirusError) as exc:
        require_clean_user_upload(data=b"%PDF-1.4", upload_type="vault")
    assert exc.value.code == AntivirusErrorCode.ANTIVIRUS_UNAVAILABLE
    assert exc.value.http_status == 503


def test_timeout_fail_closed(monkeypatch, antivirus_enabled):
    install_fake_clamd(monkeypatch, fail_mode="timeout")
    with pytest.raises(AntivirusError) as exc:
        require_clean_user_upload(data=b"%PDF-1.4", upload_type="vault")
    assert exc.value.code == AntivirusErrorCode.ANTIVIRUS_UNAVAILABLE


def test_malformed_response_fail_closed(monkeypatch, antivirus_enabled):
    install_fake_clamd(monkeypatch, response=b"not-a-clam-reply")
    with pytest.raises(AntivirusError) as exc:
        require_clean_user_upload(data=b"%PDF-1.4", upload_type="legacy_invoice")
    assert exc.value.code == AntivirusErrorCode.FILE_SCAN_FAILED
    assert exc.value.http_status == 422
