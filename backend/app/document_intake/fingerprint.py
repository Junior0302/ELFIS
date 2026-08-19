"""FileFingerprintService V2 — streaming, SHA-256 + block hashes."""

from __future__ import annotations

import hashlib
import io
import logging
import zipfile
from typing import BinaryIO

from app.document_intake.enums import FINGERPRINT_BLOCK_SIZE, ZIP_MAX_ENTRIES
from app.document_intake.validators import detect_mime

logger = logging.getLogger(__name__)


class FileFingerprintService:
    def __init__(self, *, block_size: int = FINGERPRINT_BLOCK_SIZE) -> None:
        self._block_size = max(1024, int(block_size))

    def compute_from_bytes(
        self,
        content: bytes,
        *,
        detected_mime_type: str | None = None,
        normalized_extension: str | None = None,
    ) -> dict:
        return self.compute_from_stream(
            io.BytesIO(content),
            size_hint=len(content),
            detected_mime_type=detected_mime_type or detect_mime(content),
            normalized_extension=normalized_extension,
            content_for_zip=content,
        )

    def compute_from_stream(
        self,
        stream: BinaryIO,
        *,
        size_hint: int | None = None,
        detected_mime_type: str | None = None,
        normalized_extension: str | None = None,
        content_for_zip: bytes | None = None,
    ) -> dict:
        h = hashlib.sha256()
        first_block: bytes | None = None
        last_block = b""
        total = 0
        while True:
            chunk = stream.read(self._block_size)
            if not chunk:
                break
            if first_block is None:
                first_block = chunk
            last_block = chunk
            h.update(chunk)
            total += len(chunk)

        first_hash = hashlib.sha256(first_block or b"").hexdigest() if first_block is not None else None
        last_hash = hashlib.sha256(last_block).hexdigest() if last_block else None
        sha = h.hexdigest()
        mime = detected_mime_type
        ext = (normalized_extension or "").lower().lstrip(".")
        if ext and not ext.startswith("."):
            ext = f".{ext}"

        archive_entry_count = None
        if mime == "application/zip" or ext == ".zip":
            archive_entry_count = self._zip_entry_count(content_for_zip, stream, total)

        fp = {
            "schema_version": 2,
            "sha256": sha,
            "size_bytes": size_hint if size_hint is not None else total,
            "detected_mime_type": mime,
            "normalized_extension": ext or None,
            "content_signature": None,
            "first_block_hash": first_hash,
            "last_block_hash": last_hash,
            "page_count": None,
            "first_page_hash": None,
            "last_page_hash": None,
            "archive_entry_count": archive_entry_count,
        }
        logger.info(
            "document_fingerprint_created",
            extra={
                "operation": "fingerprint",
                "size_bytes": fp["size_bytes"],
                "result": "ok",
            },
        )
        return fp

    def _zip_entry_count(
        self,
        content: bytes | None,
        stream: BinaryIO,
        total: int,
    ) -> int | None:
        try:
            data = content
            if data is None:
                pos = stream.tell()
                stream.seek(0)
                data = stream.read()
                try:
                    stream.seek(pos)
                except Exception:
                    pass
            if not data:
                return 0
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = zf.namelist()
                if len(names) > ZIP_MAX_ENTRIES:
                    raise ValueError("zip_too_many_entries")
                return len(names)
        except zipfile.BadZipFile:
            return None
        except ValueError:
            raise
        except Exception:
            return None

    @staticmethod
    def similarity_score(_a: dict, _b: dict) -> float | None:
        """Potential duplicate — non activé Sprint 2.5."""
        return None
