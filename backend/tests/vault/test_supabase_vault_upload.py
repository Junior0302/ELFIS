"""Tests Vault ↔ Supabase Storage client (mocks HTTP, pas de secrets)."""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock

import httpx
import pytest

from app.config import Settings
from app.core.supabase_storage_client import (
    SupabaseStorageClient,
    SupabaseStorageError,
    _clean_error_message,
    _mask_endpoint,
)
from app.services.vault.exceptions import VaultStorageError
from app.services.vault.storage_service import VaultStorageService


MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
SECRET = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secretpayload.signature"


def test_normalize_http_base_url_fixes_missing_slashes():
    assert Settings._normalize_http_base_url("https:proj.supabase.co") == "https://proj.supabase.co"
    assert Settings._normalize_http_base_url("http:proj.supabase.co/") == "http://proj.supabase.co"
    assert Settings._normalize_http_base_url('"https://proj.supabase.co/"') == "https://proj.supabase.co"


def test_client_normalizes_malformed_base_url_on_init():
    client = SupabaseStorageClient(
        base_url="https:proj.supabase.co",
        service_role_key=SECRET,
    )
    assert client.base_url == "https://proj.supabase.co"
    diag = client.config_diagnostics()
    assert diag["supabase_url_configured"] is True
    assert diag["url_scheme_https"] is True
    assert diag["key_length"] == len(SECRET)
    assert diag["masked_key_prefix"].endswith("...")
    assert SECRET not in diag["masked_key_prefix"]


def test_mask_endpoint_and_clean_message_redact_secrets():
    endpoint = _mask_endpoint(f"https://proj.supabase.co/storage/v1/object/elfis-vault/a.pdf")
    assert endpoint.startswith("https://HOST/")
    assert "proj.supabase.co" not in endpoint
    cleaned = _clean_error_message(f"Bearer {SECRET} rejected apikey={SECRET}")
    assert SECRET not in cleaned
    assert "REDACTED" in cleaned


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def test_upload_http_404_bucket_missing_raises_classified_error(caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("apikey") == SECRET
        assert request.headers.get("Authorization") == f"Bearer {SECRET}"
        assert request.headers.get("Content-Type") == "application/pdf"
        assert request.headers.get("x-upsert") == "false"
        assert "/storage/v1/object/elfis-vault/diagnostics/t.pdf" in str(request.url)
        return httpx.Response(
            404,
            json={"statusCode": "404", "error": "Bucket not found", "message": "Bucket not found"},
        )

    client = SupabaseStorageClient(
        base_url="https://proj.supabase.co",
        service_role_key=SECRET,
    )
    # Patch httpx.Client used inside upload_object via Monkey — override by wrapping
    original_client = httpx.Client

    class PatchedClient(original_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = _mock_transport(handler)
            super().__init__(*args, **kwargs)

    with caplog.at_level(logging.ERROR), pytest.MonkeyPatch.context() as mp:
        mp.setattr(httpx, "Client", PatchedClient)
        with pytest.raises(SupabaseStorageError) as excinfo:
            client.upload_object(
                bucket="elfis-vault",
                path="diagnostics/t.pdf",
                content=MINIMAL_PDF,
                content_type="application/pdf",
            )
    err = excinfo.value
    assert err.status_code == 404
    assert err.classification == "bucket_missing"
    assert SECRET not in caplog.text
    assert "Authorization" not in caplog.text or "Bearer" not in caplog.text


def test_upload_http_401_authentication_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "InvalidJWT", "message": "Invalid JWT"})

    original_client = httpx.Client

    class PatchedClient(original_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = _mock_transport(handler)
            super().__init__(*args, **kwargs)

    client = SupabaseStorageClient(base_url="https://proj.supabase.co", service_role_key=SECRET)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(httpx, "Client", PatchedClient)
        with pytest.raises(SupabaseStorageError) as excinfo:
            client.upload_object(
                bucket="elfis-vault",
                path="a.pdf",
                content=MINIMAL_PDF,
                content_type="application/pdf",
            )
    assert excinfo.value.classification == "authentication_failed"
    assert excinfo.value.status_code == 401


def test_upload_http_413_payload_too_large():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(413, json={"error": "Payload too large", "message": "too large"})

    original_client = httpx.Client

    class PatchedClient(original_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = _mock_transport(handler)
            super().__init__(*args, **kwargs)

    client = SupabaseStorageClient(base_url="https://proj.supabase.co", service_role_key=SECRET)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(httpx, "Client", PatchedClient)
        with pytest.raises(SupabaseStorageError) as excinfo:
            client.upload_object(
                bucket="elfis-vault",
                path="a.pdf",
                content=MINIMAL_PDF,
                content_type="application/pdf",
            )
    assert excinfo.value.classification == "payload_too_large"
    assert excinfo.value.status_code == 413


def test_upload_strips_leading_slash_from_path():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"Key": "ok"})

    original_client = httpx.Client

    class PatchedClient(original_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = _mock_transport(handler)
            super().__init__(*args, **kwargs)

    client = SupabaseStorageClient(base_url="https://proj.supabase.co", service_role_key=SECRET)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(httpx, "Client", PatchedClient)
        client.upload_object(
            bucket="elfis-vault",
            path="/entreprises/1/2026/factures/a.pdf",
            content=MINIMAL_PDF,
            content_type="application/pdf",
        )
    assert "/object/elfis-vault/entreprises/1/2026/factures/a.pdf" in seen["url"]
    assert "/elfis-vault//entreprises" not in seen["url"]


def test_upload_invalid_url_protocol_classified(monkeypatch):
    client = SupabaseStorageClient(base_url="https://proj.supabase.co", service_role_key=SECRET)

    class BoomClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise httpx.UnsupportedProtocol("Request URL is missing an 'http://' or 'https://' protocol.")

    monkeypatch.setattr(httpx, "Client", BoomClient)
    with pytest.raises(SupabaseStorageError) as excinfo:
        client.upload_object(
            bucket="elfis-vault",
            path="a.pdf",
            content=MINIMAL_PDF,
            content_type="application/pdf",
        )
    assert excinfo.value.classification == "invalid_url"


def test_signed_url_and_download_success_paths():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "/object/sign/" in str(request.url):
            return httpx.Response(200, json={"signedURL": "/object/sign/token"})
        if request.method == "GET":
            return httpx.Response(200, content=MINIMAL_PDF)
        return httpx.Response(500, json={"message": "unexpected"})

    original_client = httpx.Client

    class PatchedClient(original_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = _mock_transport(handler)
            super().__init__(*args, **kwargs)

    client = SupabaseStorageClient(base_url="https://proj.supabase.co", service_role_key=SECRET)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(httpx, "Client", PatchedClient)
        signed = client.create_signed_url(bucket="elfis-vault", path="a.pdf", expires_in=60)
        assert signed.startswith("https://proj.supabase.co/storage/v1")
        data = client.download_object(bucket="elfis-vault", path="a.pdf")
    assert data == MINIMAL_PDF


def test_vault_storage_service_maps_upload_error_without_leaking_secret(caplog):
    client = MagicMock()
    client.configured = True
    client.config_diagnostics.return_value = {
        "supabase_url_configured": True,
        "service_role_configured": True,
        "key_length": 10,
        "masked_key_prefix": "eyJhbGci...",
    }
    client.upload_object.side_effect = SupabaseStorageError(
        "Storage upload échoué (HTTP 404)",
        status_code=404,
        error_code="Bucket not found",
        classification="bucket_missing",
        bucket="elfis-vault",
        path="entreprises/1/x.pdf",
        endpoint="https://HOST/storage/v1/object/elfis-vault/entreprises/1/x.pdf",
    )
    svc = VaultStorageService(client=client, bucket="elfis-vault")
    with caplog.at_level(logging.ERROR):
        with pytest.raises(VaultStorageError):
            svc.upload_pdf(storage_path="entreprises/1/x.pdf", content=MINIMAL_PDF)
    assert "vault_storage_upload_error" in caplog.text
    assert SECRET not in caplog.text
    # Ensure structured extras were attached on the LogRecord
    records = [r for r in caplog.records if r.getMessage() == "vault_storage_upload_error"]
    assert records
    assert getattr(records[0], "status_code", None) == 404
    assert getattr(records[0], "classification", None) == "bucket_missing"


def test_vault_storage_not_configured_still_raises():
    client = MagicMock()
    client.configured = False
    client.config_diagnostics.return_value = {
        "supabase_url_configured": False,
        "service_role_configured": False,
        "key_length": 0,
        "masked_key_prefix": "EMPTY",
    }
    svc = VaultStorageService(client=client, bucket="elfis-vault")
    with pytest.raises(VaultStorageError):
        svc.upload_pdf(storage_path="a.pdf", content=MINIMAL_PDF)
