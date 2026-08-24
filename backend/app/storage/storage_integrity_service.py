"""Vérification d'intégrité StorageObjects."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.storage.storage_models import ElfisStorageObject
from app.storage.storage_registry import build_storage_provider
from app.storage.storage_types import StorageObjectStatus

logger = logging.getLogger(__name__)


@dataclass
class IntegrityFinding:
    storage_object_id: str
    provider: str
    ok: bool
    issue: str | None = None
    size_bytes: int | None = None
    checksum_ok: bool | None = None


@dataclass
class IntegrityReport:
    preview: bool
    mode: str
    scanned: int = 0
    ok: int = 0
    failed: int = 0
    findings: list[IntegrityFinding] = field(default_factory=list)


class StorageIntegrityService:
    def __init__(self, db: Session, *, audit_logger: Any | None = None) -> None:
        self._db = db
        self._audit = audit_logger

    def verify(
        self,
        *,
        provider: str | None = None,
        organization_id: int | None = None,
        limit: int = 100,
        full_checksum: bool = False,
        preview: bool = True,
    ) -> IntegrityReport:
        mode = "full-checksum" if full_checksum else "metadata-only"
        report = IntegrityReport(preview=preview, mode=mode)
        q = self._db.query(ElfisStorageObject).filter(
            ElfisStorageObject.status.in_(
                [
                    StorageObjectStatus.AVAILABLE.value,
                    StorageObjectStatus.QUARANTINED.value,
                ]
            )
        )
        if provider:
            q = q.filter(ElfisStorageObject.provider == provider)
        if organization_id is not None:
            q = q.filter(ElfisStorageObject.organization_id == organization_id)
        rows = q.order_by(ElfisStorageObject.created_at.asc()).limit(max(1, min(limit, 500))).all()

        for obj in rows:
            report.scanned += 1
            finding = self._check_one(obj, full_checksum=full_checksum)
            if finding.ok:
                report.ok += 1
            else:
                report.failed += 1
                if len(report.findings) < 100:
                    report.findings.append(finding)

        if self._audit:
            try:
                self._audit.record_storage_integrity_check_completed(
                    scanned=report.scanned,
                    failed=report.failed,
                    mode=mode,
                    preview=preview,
                )
            except Exception:
                logger.debug("integrity_audit_failed", exc_info=True)
        return report

    def _check_one(self, obj: ElfisStorageObject, *, full_checksum: bool) -> IntegrityFinding:
        try:
            provider = build_storage_provider(obj.provider)
            exists = provider.object_exists(namespace=obj.namespace, object_key=obj.object_key)
            if not exists:
                return IntegrityFinding(
                    storage_object_id=obj.id,
                    provider=obj.provider,
                    ok=False,
                    issue="object_missing",
                )
            meta = provider.get_metadata(namespace=obj.namespace, object_key=obj.object_key)
            if meta.size_bytes and obj.size_bytes and int(meta.size_bytes) != int(obj.size_bytes):
                if meta.size_bytes > 0:
                    return IntegrityFinding(
                        storage_object_id=obj.id,
                        provider=obj.provider,
                        ok=False,
                        issue="size_mismatch",
                        size_bytes=meta.size_bytes,
                    )
            checksum_ok = None
            if full_checksum and obj.checksum_sha256:
                hasher = hashlib.sha256()
                with provider.open_stream(namespace=obj.namespace, object_key=obj.object_key) as fh:
                    while True:
                        chunk = fh.read(65536)
                        if not chunk:
                            break
                        hasher.update(chunk)
                checksum_ok = hasher.hexdigest().lower() == obj.checksum_sha256.lower()
                if not checksum_ok:
                    return IntegrityFinding(
                        storage_object_id=obj.id,
                        provider=obj.provider,
                        ok=False,
                        issue="checksum_mismatch",
                        checksum_ok=False,
                    )
            return IntegrityFinding(
                storage_object_id=obj.id,
                provider=obj.provider,
                ok=True,
                size_bytes=meta.size_bytes,
                checksum_ok=checksum_ok,
            )
        except Exception as exc:
            return IntegrityFinding(
                storage_object_id=obj.id,
                provider=obj.provider,
                ok=False,
                issue=type(exc).__name__,
            )
