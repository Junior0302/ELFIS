"""Validation centralisée des fichiers uploadés."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from app.security.security_exceptions import SecurityError
from app.security.security_types import ErrorCode

_DANGEROUS_NAME = re.compile(r"[\\/<>:\"|?*\x00-\x1f]")
_DOUBLE_EXT = re.compile(r"\.(?:php|exe|sh|bat|cmd|js|html|htm|svg)\.[^.]+$", re.I)

ALLOWED_PDF = {".pdf"}
ALLOWED_IMAGES = {".png", ".jpg", ".jpeg"}
ALLOWED_TEXT = {".txt"}

PDF_MAGIC = b"%PDF"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"


@dataclass
class UploadedFileValidation:
    filename: str
    extension: str
    content_type: str
    size: int
    kind: str  # pdf | image | text


def _safe_basename(filename: str) -> str:
    raw = filename or ""
    normalized = raw.replace("\\", "/")
    if ".." in normalized or "/" in normalized:
        raise SecurityError(
            ErrorCode.UNSUPPORTED_FILE_TYPE,
            "Chemin de fichier refusé",
            status_code=400,
            details={"reason": "path_traversal"},
        )
    name = normalized.strip()
    if not name or name in {".", ".."}:
        raise SecurityError(
            ErrorCode.UNSUPPORTED_FILE_TYPE,
            "Nom de fichier invalide",
            status_code=400,
            details={"reason": "invalid_name"},
        )
    if _DANGEROUS_NAME.search(name):
        raise SecurityError(
            ErrorCode.UNSUPPORTED_FILE_TYPE,
            "Nom de fichier dangereux refusé",
            status_code=400,
            details={"reason": "dangerous_name"},
        )
    if _DOUBLE_EXT.search(name):
        raise SecurityError(
            ErrorCode.UNSUPPORTED_FILE_TYPE,
            "Double extension refusée",
            status_code=400,
            details={"reason": "double_extension"},
        )
    return name


def validate_uploaded_file(
    *,
    filename: str,
    content_type: str | None,
    content: bytes,
    max_bytes: int,
    allow_images: bool = False,
    allow_text: bool = False,
) -> UploadedFileValidation:
    if content is None or len(content) == 0:
        raise SecurityError(
            ErrorCode.VALIDATION_ERROR,
            "Fichier vide",
            status_code=400,
            details={"reason": "empty_file"},
        )
    if len(content) > max_bytes:
        raise SecurityError(
            ErrorCode.PAYLOAD_TOO_LARGE,
            "Fichier trop volumineux",
            status_code=413,
            details={"max_bytes": max_bytes, "size": len(content)},
        )

    safe_name = _safe_basename(filename)
    ext = PurePosixPath(safe_name).suffix.lower()
    mime = (content_type or "").split(";")[0].strip().lower()

    allowed_ext = set(ALLOWED_PDF)
    if allow_images:
        allowed_ext |= ALLOWED_IMAGES
    if allow_text:
        allowed_ext |= ALLOWED_TEXT

    if ext not in allowed_ext:
        raise SecurityError(
            ErrorCode.UNSUPPORTED_FILE_TYPE,
            "Type de fichier non supporté",
            status_code=400,
            details={"extension": ext},
        )

    kind = "pdf"
    if ext in ALLOWED_IMAGES:
        kind = "image"
    elif ext in ALLOWED_TEXT:
        kind = "text"

    # Signature binaire (ne pas se fier uniquement à l'extension)
    if kind == "pdf":
        if not content.startswith(PDF_MAGIC):
            raise SecurityError(
                ErrorCode.UNSUPPORTED_FILE_TYPE,
                "Signature PDF invalide",
                status_code=400,
                details={"reason": "bad_magic"},
            )
        if mime and mime not in {"application/pdf", "application/x-pdf", "application/octet-stream"}:
            raise SecurityError(
                ErrorCode.UNSUPPORTED_FILE_TYPE,
                "MIME incohérent avec PDF",
                status_code=400,
                details={"mime": mime},
            )
        # PDF chiffré (heuristique)
        head = content[:2048]
        if b"/Encrypt" in head:
            raise SecurityError(
                ErrorCode.UNSUPPORTED_FILE_TYPE,
                "PDF chiffré non supporté",
                status_code=400,
                details={"reason": "encrypted_pdf"},
            )
    elif kind == "image":
        if ext == ".png" and not content.startswith(PNG_MAGIC):
            raise SecurityError(
                ErrorCode.UNSUPPORTED_FILE_TYPE,
                "Signature PNG invalide",
                status_code=400,
                details={"reason": "bad_magic"},
            )
        if ext in {".jpg", ".jpeg"} and not content.startswith(JPEG_MAGIC):
            raise SecurityError(
                ErrorCode.UNSUPPORTED_FILE_TYPE,
                "Signature JPEG invalide",
                status_code=400,
                details={"reason": "bad_magic"},
            )
        if mime and not mime.startswith("image/") and mime != "application/octet-stream":
            raise SecurityError(
                ErrorCode.UNSUPPORTED_FILE_TYPE,
                "MIME incohérent avec image",
                status_code=400,
                details={"mime": mime},
            )
    elif kind == "text":
        if mime and mime not in {"text/plain", "application/octet-stream"}:
            raise SecurityError(
                ErrorCode.UNSUPPORTED_FILE_TYPE,
                "MIME incohérent avec texte",
                status_code=400,
                details={"mime": mime},
            )

    return UploadedFileValidation(
        filename=safe_name,
        extension=ext,
        content_type=mime or "application/octet-stream",
        size=len(content),
        kind=kind,
    )


class AntivirusScannerProtocol:
    """Interface future — non implémentée en V1."""

    def scan(self, content: bytes, *, filename: str) -> dict:
        return {"status": "skipped", "engine": "none"}
