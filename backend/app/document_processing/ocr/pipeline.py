"""Helpers pipeline OCR — tempfile sécurisé + artefact storage."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.document_processing.ocr.policies import OCRLimits
from app.document_processing.ocr.provider import OCRProviderResult
from app.document_processing.ocr.types import OCR_SCHEMA_VERSION
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_models import ElfisStorageObject

logger = logging.getLogger(__name__)


def materialize_temp_file(
    *,
    size_bytes: int | None,
    open_stream,
    limits: OCRLimits,
) -> Path:
    if size_bytes and int(size_bytes) > limits.max_file_size_bytes:
        raise ValueError("file_too_large")

    fd, name = tempfile.mkstemp(prefix="elfis-ocr-", suffix=".bin")
    path = Path(name)
    total = 0
    try:
        with os.fdopen(fd, "wb") as out:
            with open_stream() as fh:
                while True:
                    chunk = fh.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > limits.max_file_size_bytes:
                        raise ValueError("file_too_large")
                    out.write(chunk)
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass
        return path
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def build_artifact_payload(
    *,
    document_version_id: str,
    provider_key: str,
    provider_version: str,
    extraction_method: str,
    result: OCRProviderResult,
) -> tuple[bytes, str, int]:
    payload = {
        "schema_version": OCR_SCHEMA_VERSION,
        "document_version_id": document_version_id,
        "provider": provider_key,
        "provider_version": provider_version,
        "extraction_method": extraction_method,
        "pages": [
            {
                "page_number": p.page_number,
                "text": p.text,
                "confidence": p.confidence,
            }
            for p in result.pages
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    checksum = hashlib.sha256(raw).hexdigest()
    return raw, checksum, len(raw)


def store_ocr_artifact(
    db: Session,
    *,
    organization_id: int,
    ocr_result_id: str,
    content: bytes,
    checksum: str,
    limits: OCRLimits,
) -> ElfisStorageObject:
    if len(content) > limits.artifact_max_bytes:
        raise ValueError("artifact_too_large")

    namespace = (
        getattr(settings, "document_ocr_artifact_namespace", None) or "processing-artifacts"
    ).strip()
    root = Path(
        getattr(settings, "storage_local_root", None)
        or str(Path(tempfile.gettempdir()) / "elfis_storage")
    )
    root.mkdir(parents=True, exist_ok=True)
    provider = LocalStorageProvider(root=root)
    object_key = f"{uuid4().hex}/{uuid4().hex}.json"
    provider.put_object(
        namespace=namespace,
        object_key=object_key,
        data=content,
        content_type="application/json",
        metadata={"checksum_sha256": checksum},
        overwrite=True,
    )
    obj = ElfisStorageObject(
        id=str(uuid4()),
        provider="local",
        namespace=namespace,
        object_key=object_key,
        original_filename="ocr_text.json",
        safe_filename="ocr_text.json",
        mime_type_declared="application/json",
        mime_type_detected="application/json",
        extension="json",
        size_bytes=len(content),
        checksum_sha256=checksum,
        status="available",
        organization_id=organization_id,
        metadata_json={"purpose": "ocr_artifact", "ocr_result_id": ocr_result_id},
    )
    db.add(obj)
    db.flush()
    return obj


def read_artifact_bytes(storage_object: ElfisStorageObject) -> bytes:
    root = Path(
        getattr(settings, "storage_local_root", None)
        or str(Path(tempfile.gettempdir()) / "elfis_storage")
    )
    provider = LocalStorageProvider(root=root)
    return provider.get_object(namespace=storage_object.namespace, object_key=storage_object.object_key)


def delete_artifact_bytes(storage_object: ElfisStorageObject) -> None:
    """Supprime le blob OCR — jamais de chemin dans les logs."""
    root = Path(
        getattr(settings, "storage_local_root", None)
        or str(Path(tempfile.gettempdir()) / "elfis_storage")
    )
    provider = LocalStorageProvider(root=root)
    try:
        provider.delete_object(namespace=storage_object.namespace, object_key=storage_object.object_key)
    except Exception:
        logger.warning("ocr_artifact_delete_failed", extra={"storage_object_id": storage_object.id})
        raise

