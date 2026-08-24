"""Tests unitaires SupabaseStorageProvider — client mocké (httpx MockTransport)."""

from __future__ import annotations

import io

import httpx
import pytest

from app.storage.providers.supabase_http_client import SupabaseStorageHttpClient
from app.storage.providers.supabase_storage_provider import SupabaseStorageProvider
from app.storage.storage_exceptions import StorageProviderError


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def _client_ok():
    store: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and "/object/" in path and "/list/" not in path and "/sign/" not in path:
            # upload
            key = path.split("/object/", 1)[1]
            body = request.read()
            if key in store and request.headers.get("x-upsert") == "false":
                return httpx.Response(409, json={"error": "exists"})
            store[key] = body
            return httpx.Response(200, json={"Key": key})
        if request.method == "GET" and "/object/" in path:
            key = path.split("/object/", 1)[1]
            if key not in store:
                return httpx.Response(404, json={"error": "not_found"})
            return httpx.Response(200, content=store[key])
        if request.method == "DELETE":
            return httpx.Response(200, json={})
        if request.method == "POST" and "/list/" in path:
            return httpx.Response(200, json=[])
        if request.method == "POST" and "/sign/" in path:
            return httpx.Response(200, json={"signedURL": "/object/sign/test"})
        return httpx.Response(404)

    client = SupabaseStorageHttpClient(
        base_url="https://example.supabase.co",
        service_role_key="secret-test-key",
        timeout=5.0,
        max_retries=0,
        transport=_mock_transport(handler),
    )
    return client, store


def test_config_incomplete_raises():
    with pytest.raises(StorageProviderError):
        SupabaseStorageProvider(
            client=SupabaseStorageHttpClient(base_url="", service_role_key=""),
            bucket="b",
        )


def test_upload_download_delete_stream():
    client, store = _client_ok()
    provider = SupabaseStorageProvider(client=client, bucket="elfis-documents")
    assert provider.capabilities.supports_signed_urls
    assert provider.capabilities.prefers_local_temp_then_remote_put

    ref = provider.put_object(
        namespace="documents",
        object_key="org/1/a.pdf",
        data=b"%PDF-1.4",
        content_type="application/pdf",
    )
    assert ref.provider == "supabase"
    assert provider.object_exists(namespace="documents", object_key="org/1/a.pdf")

    data = provider.get_object(namespace="documents", object_key="org/1/a.pdf")
    assert data.startswith(b"%PDF")

    with provider.open_stream(namespace="documents", object_key="org/1/a.pdf") as fh:
        assert fh.read(4) == b"%PDF"

    assert provider.delete_object(namespace="documents", object_key="org/1/a.pdf") is True


def test_put_stream_from_fileobj():
    client, _ = _client_ok()
    provider = SupabaseStorageProvider(client=client, bucket="elfis-documents")
    buf = io.BytesIO(b"hello-stream")
    ref = provider.put_stream(
        namespace="documents",
        object_key="x/y.bin",
        stream=buf,
        size_bytes=12,
        content_type="application/octet-stream",
    )
    assert ref.size_bytes == 12


def test_conflict_no_overwrite():
    client, _ = _client_ok()
    provider = SupabaseStorageProvider(client=client, bucket="elfis-documents")
    provider.put_object(namespace="documents", object_key="same", data=b"a")
    with pytest.raises(StorageProviderError) as ei:
        provider.put_object(namespace="documents", object_key="same", data=b"b", overwrite=False)
    assert ei.value.code == "object_exists"


def test_no_secret_in_health_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    client = SupabaseStorageHttpClient(
        base_url="https://example.supabase.co",
        service_role_key="super-secret-should-not-leak",
        transport=_mock_transport(handler),
        max_retries=0,
    )
    provider = SupabaseStorageProvider(client=client, bucket="b")
    result = provider.health_check()
    assert result["probe_ok"] is False
    blob = str(result)
    assert "super-secret" not in blob


def test_capabilities_model():
    client, _ = _client_ok()
    provider = SupabaseStorageProvider(client=client, bucket="b")
    caps = provider.capabilities
    assert caps.supports_atomic_move is False
    assert caps.supports_signed_urls is True
