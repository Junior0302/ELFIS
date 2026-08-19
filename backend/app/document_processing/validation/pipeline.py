"""Artefacts validation métier."""

from __future__ import annotations

import hashlib
import json
import logging
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.document_processing.validation.policies import ValidationLimits
from app.document_processing.validation.types import BUSINESS_VALIDATION_ARTIFACT_SCHEMA
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_models import ElfisStorageObject

logger = logging.getLogger(__name__)


def build_validation_artifact(
    *,
    document_version_id: str,
    extraction_result_id: str,
    rule_set_key: str,
    rule_set_version: str,
    status: str,
    issues: list[dict[str, Any]],
) -> tuple[bytes, str]:
    payload = {
        "schema_version": BUSINESS_VALIDATION_ARTIFACT_SCHEMA,
        "document_version_id": document_version_id,
        "extraction_result_id": extraction_result_id,
        "rule_set": {"key": rule_set_key, "version": rule_set_version},
        "status": status,
        "issues": issues,
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return raw, hashlib.sha256(raw).hexdigest()


def store_validation_artifact(
    db: Session,
    *,
    organization_id: int,
    validation_id: str,
    content: bytes,
    checksum: str,
    limits: ValidationLimits,
) -> ElfisStorageObject:
    if len(content) > limits.max_artifact_bytes:
        raise ValueError("artifact_too_large")
    root = Path(
        getattr(settings, "storage_local_root", None)
        or str(Path(tempfile.gettempdir()) / "elfis_storage")
    )
    root.mkdir(parents=True, exist_ok=True)
    provider = LocalStorageProvider(root=root)
    object_key = f"{uuid4().hex}/{uuid4().hex}.json"
    provider.put_object(
        namespace=limits.artifact_namespace,
        object_key=object_key,
        data=content,
        content_type="application/json",
        metadata={"checksum_sha256": checksum},
        overwrite=True,
    )
    obj = ElfisStorageObject(
        id=str(uuid4()),
        provider="local",
        namespace=limits.artifact_namespace,
        object_key=object_key,
        original_filename="business_validation.json",
        safe_filename="business_validation.json",
        mime_type_declared="application/json",
        mime_type_detected="application/json",
        extension="json",
        size_bytes=len(content),
        checksum_sha256=checksum,
        status="available",
        organization_id=organization_id,
        metadata_json={"purpose": "business_validation", "validation_id": validation_id},
    )
    db.add(obj)
    db.flush()
    return obj


def delete_validation_artifact(storage_object: ElfisStorageObject) -> None:
    root = Path(
        getattr(settings, "storage_local_root", None)
        or str(Path(tempfile.gettempdir()) / "elfis_storage")
    )
    provider = LocalStorageProvider(root=root)
    try:
        provider.delete_object(namespace=storage_object.namespace, object_key=storage_object.object_key)
    except Exception:
        logger.warning("bv_artifact_delete_failed", extra={"storage_object_id": storage_object.id})
        raise


def store_json_draft(
    db: Session,
    *,
    organization_id: int,
    job_id: str,
    payload: dict,
    limits: ValidationLimits,
    purpose: str,
) -> ElfisStorageObject:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    checksum = hashlib.sha256(raw).hexdigest()
    return store_validation_artifact(
        db,
        organization_id=organization_id,
        validation_id=job_id,
        content=raw,
        checksum=checksum,
        limits=limits,
    )


def read_json_artifact(obj: ElfisStorageObject) -> dict:
    root = Path(
        getattr(settings, "storage_local_root", None)
        or str(Path(tempfile.gettempdir()) / "elfis_storage")
    )
    provider = LocalStorageProvider(root=root)
    data = provider.get_object(namespace=obj.namespace, object_key=obj.object_key)
    return json.loads(data.decode("utf-8"))
