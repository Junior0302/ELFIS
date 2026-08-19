"""Helpers Phase C — pipeline documents (Vault → DI → AI → Accounting)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.events.event_worker import EventWorker
from app.jobs.job_worker import JobWorker
from app.services.vault.exceptions import VaultStorageError


class InMemoryVaultStorage:
    """Stockage mock partagé upload ↔ download — aucun réseau."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload_pdf(self, *, storage_path: str, content: bytes) -> str:
        if not content:
            raise VaultStorageError("contenu vide")
        self.objects[storage_path] = content
        return storage_path

    def download_bytes(self, *, storage_path: str) -> bytes:
        if storage_path not in self.objects:
            raise VaultStorageError("objet introuvable")
        return self.objects[storage_path]

    def delete_file(self, *, storage_path: str) -> None:
        self.objects.pop(storage_path, None)

    def create_signed_url(self, *, storage_path: str, ttl_seconds: int = 300) -> str:
        return f"https://mock-vault.test/{storage_path}?ttl={ttl_seconds}&sig=recette"


def install_mock_vault_storage(monkeypatch, storage: InMemoryVaultStorage | None = None) -> InMemoryVaultStorage:
    """Branche le stockage mémoire sur Vault + Document Intelligence."""
    store = storage or InMemoryVaultStorage()

    def _factory(*_a, **_k):
        return store

    monkeypatch.setattr("app.services.vault.vault_service.VaultStorageService", _factory)
    monkeypatch.setattr(
        "app.document_intelligence.document_service.VaultStorageService",
        _factory,
    )
    return store


def assert_safe_document_body(body: Any) -> None:
    blob = str(body).lower()
    for forbidden in (
        "sk_",
        "openai",
        "traceback",
        "authorization",
        "bearer ",
        "password",
        "supabase",
        "c:\\users",
        "/home/",
        "select * from",
    ):
        assert forbidden not in blob, f"fuite suspecte: {forbidden}"


def drain_pipeline(
    Session: sessionmaker,
    *,
    max_rounds: int = 25,
    worker_id: str | None = None,
) -> dict[str, int]:
    """Exécute jobs + events en synchrone jusqu’à quiescence."""
    from app.events import bootstrap_handlers
    from app.jobs import bootstrap_job_handlers

    bootstrap_job_handlers()
    bootstrap_handlers()
    wid = worker_id or f"phase-c-{uuid4().hex[:8]}"
    jobs_done = 0
    events_done = 0
    for _ in range(max_rounds):
        db: Session = Session()
        try:
            jn = JobWorker(db, worker_id=f"{wid}-j", session_factory=Session).process_next_batch()
            en = EventWorker(db, worker_id=f"{wid}-e").process_next_batch()
            db.commit()
            jobs_done += int(jn or 0)
            events_done += int(en or 0)
            if (jn or 0) == 0 and (en or 0) == 0:
                break
        finally:
            db.close()
    return {"jobs": jobs_done, "events": events_done}


def doc_id_from_archive(payload: dict[str, Any]) -> str:
    return str(payload.get("id") or payload.get("document_id") or "")
