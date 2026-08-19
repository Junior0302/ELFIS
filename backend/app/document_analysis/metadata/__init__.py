"""Lecture métadonnées document — sans mutation."""

from __future__ import annotations

from typing import Any


def analyze_metadata(
    *,
    filename: str,
    size_bytes: int,
    mime: str | None,
    extension: str | None,
    checksum_sha256: str | None,
    fingerprint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fp = fingerprint or {}
    return {
        "original_filename": filename,
        "size_bytes": size_bytes,
        "declared_mime": mime,
        "extension": extension,
        "checksum_sha256": checksum_sha256,
        "fingerprint_version": fp.get("schema_version"),
        "first_block_hash": fp.get("first_block_hash"),
        "last_block_hash": fp.get("last_block_hash"),
    }
