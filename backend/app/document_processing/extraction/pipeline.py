"""Artefacts extraction — persistés (pas de cache process-local seul)."""

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
from app.document_processing.extraction.policies import ExtractionLimits
from app.document_processing.extraction.provider import ExtractionProviderResult
from app.document_processing.extraction.types import EXTRACTION_ARTIFACT_SCHEMA
from app.document_processing.extraction.validation import SchemaValidationResult
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_models import ElfisStorageObject

logger = logging.getLogger(__name__)


def build_extraction_artifact_payload(
    *,
    document_version_id: str,
    ocr_result_id: str | None,
    schema_key: str,
    schema_version: str,
    provider_key: str,
    provider_version: str,
    result: ExtractionProviderResult,
    validation: SchemaValidationResult | None,
    corrections: dict[str, Any] | None = None,
) -> tuple[bytes, str, int]:
    fields_out: dict[str, Any] = {}
    for path, f in (result.fields or {}).items():
        fields_out[path] = f.to_public_dict()
        if corrections and path in corrections:
            fields_out[path]["provider_value"] = fields_out[path].get("value")
            fields_out[path]["corrected_value"] = corrections[path].get("corrected_value")
            fields_out[path]["manually_corrected"] = True

    payload = {
        "schema": EXTRACTION_ARTIFACT_SCHEMA,
        "schema_key": schema_key,
        "schema_version": schema_version,
        "document_version_id": document_version_id,
        "ocr_result_id": ocr_result_id,
        "provider": {"key": provider_key, "version": provider_version},
        "fields": fields_out,
        "validation": validation.to_summary_dict() if validation else None,
        "warnings": list(result.warnings or [])[:20],
        "confidence_score": result.confidence_score,
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    checksum = hashlib.sha256(raw).hexdigest()
    return raw, checksum, len(raw)


def store_extraction_artifact(
    db: Session,
    *,
    organization_id: int,
    extraction_result_id: str,
    content: bytes,
    checksum: str,
    limits: ExtractionLimits,
    purpose: str = "extraction_artifact",
) -> ElfisStorageObject:
    if len(content) > limits.max_result_bytes:
        raise ValueError("artifact_too_large")

    namespace = limits.artifact_namespace
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
        original_filename="extraction.json",
        safe_filename="extraction.json",
        mime_type_declared="application/json",
        mime_type_detected="application/json",
        extension="json",
        size_bytes=len(content),
        checksum_sha256=checksum,
        status="available",
        organization_id=organization_id,
        metadata_json={"purpose": purpose, "extraction_result_id": extraction_result_id},
    )
    db.add(obj)
    db.flush()
    return obj


def read_extraction_artifact_bytes(storage_object: ElfisStorageObject) -> bytes:
    root = Path(
        getattr(settings, "storage_local_root", None)
        or str(Path(tempfile.gettempdir()) / "elfis_storage")
    )
    provider = LocalStorageProvider(root=root)
    return provider.get_object(namespace=storage_object.namespace, object_key=storage_object.object_key)


def delete_extraction_artifact_bytes(storage_object: ElfisStorageObject) -> None:
    root = Path(
        getattr(settings, "storage_local_root", None)
        or str(Path(tempfile.gettempdir()) / "elfis_storage")
    )
    provider = LocalStorageProvider(root=root)
    try:
        provider.delete_object(namespace=storage_object.namespace, object_key=storage_object.object_key)
    except Exception:
        logger.warning(
            "extraction_artifact_delete_failed",
            extra={"storage_object_id": storage_object.id},
        )
        raise


def store_text_draft_artifact(
    db: Session,
    *,
    organization_id: int,
    job_id: str,
    text: str,
    page_metadata: list,
    limits: ExtractionLimits,
) -> ElfisStorageObject:
    """Source texte persistée entre steps — survit à un changement de worker."""
    payload = {
        "schema": "extraction_source_draft_v1",
        "job_id": job_id,
        "text": text,
        "pages": page_metadata,
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    checksum = hashlib.sha256(raw).hexdigest()
    return store_extraction_artifact(
        db,
        organization_id=organization_id,
        extraction_result_id=job_id,
        content=raw,
        checksum=checksum,
        limits=limits,
        purpose="extraction_source_draft",
    )


def store_provider_draft_artifact(
    db: Session,
    *,
    organization_id: int,
    job_id: str,
    provider_payload: dict,
    limits: ExtractionLimits,
) -> ElfisStorageObject:
    raw = json.dumps(provider_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    checksum = hashlib.sha256(raw).hexdigest()
    return store_extraction_artifact(
        db,
        organization_id=organization_id,
        extraction_result_id=job_id,
        content=raw,
        checksum=checksum,
        limits=limits,
        purpose="extraction_provider_draft",
    )


def read_json_artifact(storage_object: ElfisStorageObject) -> dict:
    data = read_extraction_artifact_bytes(storage_object)
    return json.loads(data.decode("utf-8"))
