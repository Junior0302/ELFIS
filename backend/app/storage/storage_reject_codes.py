"""Codes de rejet stables — Upload Storage RC2.4 étape 2."""

from __future__ import annotations

from enum import Enum


class StorageRejectCode(str, Enum):
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    EMPTY_FILE = "EMPTY_FILE"
    BLOCKED_EXTENSION = "BLOCKED_EXTENSION"
    MIME_MISMATCH = "MIME_MISMATCH"
    INVALID_FILENAME = "INVALID_FILENAME"
    UNSUPPORTED_TYPE = "UNSUPPORTED_TYPE"
    SECURITY_POLICY_REJECTED = "SECURITY_POLICY_REJECTED"
    UPLOAD_INTERRUPTED = "UPLOAD_INTERRUPTED"
    METADATA_INVALID = "METADATA_INVALID"
    ORGANIZATION_REQUIRED = "ORGANIZATION_REQUIRED"


# Mapping codes internes historiques → codes stables
_LEGACY_MAP = {
    "empty_file": StorageRejectCode.EMPTY_FILE,
    "file_too_large": StorageRejectCode.FILE_TOO_LARGE,
    "blocked_extension": StorageRejectCode.BLOCKED_EXTENSION,
    "double_extension": StorageRejectCode.BLOCKED_EXTENSION,
    "dangerous_filename": StorageRejectCode.INVALID_FILENAME,
    "invalid_filename": StorageRejectCode.INVALID_FILENAME,
    "mime_not_allowed": StorageRejectCode.UNSUPPORTED_TYPE,
    "mime_mismatch": StorageRejectCode.MIME_MISMATCH,
    "upload_interrupted": StorageRejectCode.UPLOAD_INTERRUPTED,
    "security_policy_rejected": StorageRejectCode.SECURITY_POLICY_REJECTED,
    "metadata_invalid": StorageRejectCode.METADATA_INVALID,
    "organization_required": StorageRejectCode.ORGANIZATION_REQUIRED,
}


def to_reject_code(internal: str | None) -> str:
    if not internal:
        return StorageRejectCode.SECURITY_POLICY_REJECTED.value
    if internal in {c.value for c in StorageRejectCode}:
        return internal
    mapped = _LEGACY_MAP.get(internal.lower())
    return mapped.value if mapped else StorageRejectCode.SECURITY_POLICY_REJECTED.value
