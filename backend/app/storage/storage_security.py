"""Validation sécurité des fichiers uploadés (couche Storage) — RC2.4 étape 2."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from app.config import settings
from app.storage.storage_exceptions import StorageValidationError
from app.storage.storage_reject_codes import StorageRejectCode, to_reject_code

_DANGEROUS_NAME = re.compile(r"[\\/<>:\"|?*\x00-\x1f\r\n]")
_DOUBLE_EXT = re.compile(
    r"\.(?:php|exe|sh|bat|cmd|js|html|htm|svg|msi|dll|com|scr|vbs|jar|wsf)\.[^.]+$",
    re.I,
)
_ARCHIVE_EXT = frozenset({".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2"})

_MAGIC: list[tuple[str, bytes]] = [
    ("application/pdf", b"%PDF"),
    ("image/png", b"\x89PNG\r\n\x1a\n"),
    ("image/jpeg", b"\xff\xd8\xff"),
    ("image/webp", b"RIFF"),  # + WEBP at offset 8
    ("application/zip", b"PK\x03\x04"),  # also docx/xlsx
]


@dataclass(frozen=True)
class FileValidationResult:
    original_filename: str
    safe_filename: str
    extension: str
    mime_type_declared: str
    mime_type_detected: str | None
    size_bytes: int
    checksum_sha256: str | None
    quarantined: bool
    reject_reason: str | None = None


def _blocked_extensions() -> set[str]:
    raw = getattr(settings, "storage_blocked_extensions", "") or ""
    parts = {p.strip().lower() for p in str(raw).split(",") if p.strip()}
    defaults = {
        ".exe",
        ".bat",
        ".cmd",
        ".sh",
        ".ps1",
        ".msi",
        ".dll",
        ".com",
        ".scr",
        ".js",
        ".html",
        ".htm",
        ".php",
        ".svg",
        ".vbs",
        ".jar",
        ".wsf",
        ".zip",
        ".rar",
        ".7z",
    }
    return defaults | {e if e.startswith(".") else f".{e}" for e in parts}


def _allowed_mimes() -> set[str]:
    raw = getattr(settings, "storage_allowed_mime_types", "") or ""
    if raw.strip():
        return {p.strip().lower() for p in raw.split(",") if p.strip()}
    return {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
        "text/plain",
        "application/json",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }


def _raise(code: str, message: str) -> None:
    raise StorageValidationError(to_reject_code(code), message)


def safe_basename(filename: str) -> str:
    if filename is None:
        _raise("invalid_filename", "Nom de fichier invalide")
    if "\x00" in filename:
        _raise("invalid_filename", "Caractère NUL interdit")
    raw = filename.replace("\\", "/")
    name = PurePosixPath(raw).name.strip()
    if not name or name in {".", ".."} or ".." in raw.split("/"):
        _raise("invalid_filename", "Nom de fichier invalide")
    if _DANGEROUS_NAME.search(name):
        _raise("dangerous_filename", "Nom de fichier dangereux")
    if _DOUBLE_EXT.search(name):
        _raise("double_extension", "Double extension dangereuse")
    return name[:200]


def detect_mime(head: bytes, declared: str, extension: str) -> str | None:
    """Détection prudente — premiers octets uniquement."""
    if head.startswith(b"%PDF"):
        return "application/pdf"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(head) >= 12 and head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"PK\x03\x04"):
        # ZIP container — docx/xlsx selon extension, sinon archive non autorisée
        if extension == ".docx":
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if extension == ".xlsx":
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return "application/zip"
    if extension in {".txt"} and b"\x00" not in head[:1024]:
        return "text/plain"
    if extension == ".csv" and b"\x00" not in head[:1024]:
        return "text/csv"
    if extension == ".json" and head[:1] in (b"{", b"["):
        return "application/json"
    declared_l = (declared or "").split(";")[0].strip().lower()
    return declared_l or None


def validate_filename_only(filename: str) -> tuple[str, str]:
    original = safe_basename(filename)
    ext = PurePosixPath(original).suffix.lower()
    if ext in _blocked_extensions() or ext in _ARCHIVE_EXT:
        _raise("blocked_extension", f"Extension bloquée: {ext}")
    return original, ext


def validate_upload_head_and_meta(
    *,
    filename: str,
    head: bytes,
    size_bytes: int,
    declared_mime: str | None = None,
    checksum_sha256: str | None = None,
) -> FileValidationResult:
    """Validation finale après streaming (taille réelle + magic)."""
    max_size = int(getattr(settings, "storage_max_file_size_bytes", 15 * 1024 * 1024) or 15 * 1024 * 1024)
    original, ext = validate_filename_only(filename)
    declared = (declared_mime or "application/octet-stream").split(";")[0].strip().lower()

    if size_bytes <= 0:
        _raise("empty_file", "Fichier vide refusé")
    if size_bytes > max_size:
        _raise("file_too_large", f"Fichier trop volumineux (max {max_size} octets)")

    # MZ / exécutable même renommé
    if head.startswith(b"MZ"):
        _raise("security_policy_rejected", "Exécutable détecté")

    detected = detect_mime(head, declared, ext)
    allowed = _allowed_mimes()
    quarantine = bool(getattr(settings, "storage_quarantine_enabled", False))

    candidate = detected or declared
    if candidate == "application/zip" or (detected == "application/zip" and ext not in {".docx", ".xlsx"}):
        _raise("unsupported_type", "Archives non autorisées")

    if candidate not in allowed:
        if quarantine:
            return FileValidationResult(
                original_filename=original,
                safe_filename=original,
                extension=ext or "",
                mime_type_declared=declared,
                mime_type_detected=detected,
                size_bytes=size_bytes,
                checksum_sha256=checksum_sha256,
                quarantined=True,
                reject_reason=StorageRejectCode.UNSUPPORTED_TYPE.value,
            )
        _raise("mime_not_allowed", f"Type MIME non autorisé: {candidate}")

    if detected and declared not in ("application/octet-stream", "") and detected != declared:
        # extension vs magic
        ext_mime_map = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".json": "application/json",
        }
        expected = ext_mime_map.get(ext)
        if expected and detected != expected:
            if quarantine:
                return FileValidationResult(
                    original_filename=original,
                    safe_filename=original,
                    extension=ext or "",
                    mime_type_declared=declared,
                    mime_type_detected=detected,
                    size_bytes=size_bytes,
                    checksum_sha256=checksum_sha256,
                    quarantined=True,
                    reject_reason=StorageRejectCode.MIME_MISMATCH.value,
                )
            _raise("mime_mismatch", "Type MIME / extension incohérents")
        if declared.split("/")[0] != detected.split("/")[0]:
            _raise("mime_mismatch", "Type MIME déclaré incohérent")

    return FileValidationResult(
        original_filename=original,
        safe_filename=original,
        extension=ext or "",
        mime_type_declared=declared,
        mime_type_detected=detected,
        size_bytes=size_bytes,
        checksum_sha256=checksum_sha256,
        quarantined=False,
    )


def validate_upload(
    *,
    filename: str,
    content: bytes,
    declared_mime: str | None = None,
    compute_checksum: bool | None = None,
) -> FileValidationResult:
    """Compat étape 1 — charge complète (tests unitaires / petits fichiers)."""
    do_hash = (
        compute_checksum
        if compute_checksum is not None
        else bool(getattr(settings, "storage_checksum_enabled", True))
    )
    checksum = hashlib.sha256(content).hexdigest() if do_hash else None
    return validate_upload_head_and_meta(
        filename=filename,
        head=content[:64] if content else b"",
        size_bytes=len(content),
        declared_mime=declared_mime,
        checksum_sha256=checksum,
    )
