"""Tests LocalStorageProvider."""

from __future__ import annotations

import pytest

from app.storage.providers.local_storage_provider import LocalStorageProvider, new_object_key
from app.storage.storage_exceptions import StorageNotFoundError, StorageValidationError


def test_put_get_delete_stream(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    key = new_object_key(extension=".txt")
    ref = provider.put_object(namespace="ns1", object_key=key, data=b"hello-elfis")
    assert ref.size_bytes == 11
    assert provider.object_exists(namespace="ns1", object_key=key)
    assert provider.get_object(namespace="ns1", object_key=key) == b"hello-elfis"
    with provider.open_stream(namespace="ns1", object_key=key) as fh:
        assert fh.read() == b"hello-elfis"
    chunks = list(provider.iter_chunks(namespace="ns1", object_key=key, chunk_size=4))
    assert b"".join(chunks) == b"hello-elfis"
    assert provider.delete_object(namespace="ns1", object_key=key) is True
    assert provider.object_exists(namespace="ns1", object_key=key) is False


def test_path_traversal_blocked(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    with pytest.raises(StorageValidationError):
        provider.put_object(namespace="ns", object_key="../evil.txt", data=b"x")
    with pytest.raises(StorageValidationError):
        provider.get_object(namespace="ns", object_key="../../etc/passwd")


def test_object_key_is_uuid_not_filename(tmp_path):
    key = new_object_key(extension=".pdf")
    assert "invoice" not in key
    assert key.endswith(".pdf")
    assert len(key) >= 32


def test_missing_object(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    with pytest.raises(StorageNotFoundError):
        provider.get_object(namespace="ns", object_key="missing.txt")


def test_health_probe_cleans_up(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    result = provider.health_check()
    assert result["status"] == "healthy"
    assert result["probe_ok"] is True
    # aucun .probe restant
    leftovers = list(tmp_path.rglob("*.probe"))
    assert leftovers == []


def test_root_isolation(tmp_path):
    provider = LocalStorageProvider(root=tmp_path / "root_a")
    key = new_object_key(extension=".bin")
    provider.put_object(namespace="default", object_key=key, data=b"secret")
    other = LocalStorageProvider(root=tmp_path / "root_b")
    assert other.object_exists(namespace="default", object_key=key) is False
