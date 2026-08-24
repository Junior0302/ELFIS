"""Tests CLI cleanup_temp / find_orphans (preview)."""

from __future__ import annotations

from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_upload import TEMP_NAMESPACE
from scripts.storage.cleanup_temp import main as cleanup_main
from scripts.storage.find_orphans import main as orphans_main


def test_cleanup_preview(tmp_path, monkeypatch, capsys):
    provider = LocalStorageProvider(root=tmp_path)
    provider.put_object(namespace=TEMP_NAMESPACE, object_key="old.part", data=b"tmp")
    code = cleanup_main(["--preview", "--local-root", str(tmp_path), "--older-than-hours", "0"])
    assert code == 0
    out = capsys.readouterr().out
    assert "preview" in out
    assert provider.object_exists(namespace=TEMP_NAMESPACE, object_key="old.part")


def test_cleanup_requires_confirm(tmp_path, capsys):
    code = cleanup_main(["--execute", "--local-root", str(tmp_path), "--older-than-hours", "0"])
    assert code == 2


def test_cleanup_execute(tmp_path, capsys):
    provider = LocalStorageProvider(root=tmp_path)
    provider.put_object(namespace=TEMP_NAMESPACE, object_key="old.part", data=b"tmp")
    # ne pas toucher un objet available
    provider.put_object(namespace="default", object_key="keep.bin", data=b"keep")
    code = cleanup_main(
        [
            "--execute",
            "--confirm",
            "--local-root",
            str(tmp_path),
            "--older-than-hours",
            "0",
        ]
    )
    assert code == 0
    assert not provider.object_exists(namespace=TEMP_NAMESPACE, object_key="old.part")
    assert provider.object_exists(namespace="default", object_key="keep.bin")


def test_find_orphans_preview(tmp_path, capsys, monkeypatch):
    from tests.storage.conftest_helpers import make_storage_db

    factory, _ = make_storage_db()
    monkeypatch.setattr("app.database.SessionLocal", factory)
    code = orphans_main(["--preview", "--local-root", str(tmp_path)])
    assert code == 0
    out = capsys.readouterr().out
    assert "auto_delete" in out
    assert "false" in out.lower() or '"auto_delete": false' in out
