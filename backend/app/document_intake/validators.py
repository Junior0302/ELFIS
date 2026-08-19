"""Validation fichiers — Document Intake (ne pas se fier à l'extension seule)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import PurePosixPath

from app.document_intake.enums import DEFAULT_MAX_FILE_BYTES
from app.document_intake.exceptions import DocumentIntakeValidationError
from app.document_intake.format_registry import FormatDef, get_format_by_extension

_DANGEROUS = re.compile(r"[\\<>:\"|?*\x00-\x1f\r\n]")
_DOUBLE_EXT = re.compile(
    r"\.(?:php|exe|sh|bat|cmd|js|html|htm|svg|msi|dll|com|scr|vbs|jar|wsf)\.[^.]+$",
    re.I,
)

_MAGIC: list[tuple[str, bytes]] = [
    ("application/pdf", b"%PDF"),
    ("image/png", b"\x89PNG\r\n\x1a\n"),
    ("image/jpeg", b"\xff\xd8\xff"),
    ("image/tiff", b"II*\x00"),
    ("image/tiff", b"MM\x00*"),
    ("application/zip", b"PK\x03\x04"),
    ("application/zip", b"PK\x05\x06"),
    ("application/vnd.ms-excel", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),  # OLE
]


@dataclass
class ValidationResult:
    original_filename: str
    normalized_filename: str
    extension: str
    format_id: str
    declared_mime: str
    detected_mime: str | None
    size_bytes: int
    upload_allowed: bool
    preview_allowed: bool
    analysis_allowed: bool
    extract_later: bool
    mime_mismatch: bool
    relative_path: str | None


def normalize_filename(filename: str) -> str:
    raw = (filename or "").replace("\\", "/").strip()
    name = PurePosixPath(raw).name
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:240] if name else "unnamed"


def normalize_relative_path(path: str | None) -> str | None:
    if not path:
        return None
    cleaned = path.replace("\\", "/").strip().lstrip("/")
    parts = [p for p in cleaned.split("/") if p and p not in {".", ".."}]
    if not parts:
        return None
    return "/".join(parts)[:500]


def detect_mime(head: bytes) -> str | None:
    if not head:
        return None
    for mime, magic in _MAGIC:
        if head.startswith(magic):
            if mime == "application/zip" and magic == b"RIFF":
                continue
            return mime
    # Text heuristics
    sample = head[:512]
    try:
        text = sample.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = sample.decode("latin-1")
        except Exception:
            return None
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return "application/json"
    if stripped.startswith("<?xml") or stripped.startswith("<"):
        return "application/xml"
    if "," in text or ";" in text:
        return "text/csv"
    return "text/plain"


def assert_safe_name(filename: str) -> str:
    name = normalize_filename(filename)
    if not name or name in {".", ".."}:
        raise DocumentIntakeValidationError("invalid_name", "Nom de fichier invalide")
    if ".." in name or "/" in name or "\\" in name:
        raise DocumentIntakeValidationError("path_traversal", "Chemin de fichier refusé")
    if _DANGEROUS.search(name):
        raise DocumentIntakeValidationError("dangerous_name", "Caractères interdits dans le nom")
    if _DOUBLE_EXT.search(name):
        raise DocumentIntakeValidationError("double_extension", "Double extension refusée")
    return name


def validate_content(
    *,
    filename: str,
    content: bytes,
    declared_mime: str | None = None,
    relative_path: str | None = None,
    max_bytes: int | None = None,
) -> ValidationResult:
    if content is None or len(content) == 0:
        raise DocumentIntakeValidationError("empty_file", "Fichier vide")
    limit = max_bytes or DEFAULT_MAX_FILE_BYTES
    if len(content) > limit:
        raise DocumentIntakeValidationError(
            "file_too_large",
            f"Fichier trop volumineux (max {limit} octets)",
        )

    safe = assert_safe_name(filename)
    ext = PurePosixPath(safe).suffix.lower()
    fmt = get_format_by_extension(ext)
    if fmt is None or not fmt.upload_allowed:
        raise DocumentIntakeValidationError(
            "extension_not_allowed",
            f"Extension non autorisée: {ext or '(aucune)'}",
        )
    if len(content) > fmt.max_bytes:
        raise DocumentIntakeValidationError(
            "file_too_large",
            f"Fichier trop volumineux pour {fmt.id} (max {fmt.max_bytes})",
        )

    declared = (declared_mime or "").split(";")[0].strip().lower() or "application/octet-stream"
    detected = detect_mime(content[:64])
    mismatch = False
    if detected:
        # ZIP polyglot : xlsx/ods déclarent souvent application/zip
        if detected == "application/zip" and ext in {".xlsx", ".ods", ".zip"}:
            mismatch = False
        elif detected not in fmt.mime_types and declared not in fmt.mime_types:
            # Si magic ne matche aucun mime du format → quarantaine potentielle
            if detected not in fmt.mime_types:
                mismatch = True
        elif detected not in fmt.mime_types and ext not in {".xlsx", ".ods", ".csv", ".txt", ".json", ".xml"}:
            mismatch = True

    # Cas strict : PDF/JPEG/PNG/TIFF doivent matcher magic
    if ext == ".pdf" and detected != "application/pdf":
        mismatch = True
    if ext in {".jpg", ".jpeg"} and detected != "image/jpeg":
        mismatch = True
    if ext == ".png" and detected != "image/png":
        mismatch = True
    if ext in {".tif", ".tiff"} and detected != "image/tiff":
        mismatch = True
    if ext == ".zip" and detected != "application/zip":
        mismatch = True

    return ValidationResult(
        original_filename=filename,
        normalized_filename=safe,
        extension=ext,
        format_id=fmt.id,
        declared_mime=declared,
        detected_mime=detected,
        size_bytes=len(content),
        upload_allowed=fmt.upload_allowed,
        preview_allowed=fmt.preview_allowed,
        analysis_allowed=fmt.analysis_allowed,
        extract_later=fmt.extract_later,
        mime_mismatch=mismatch,
        relative_path=normalize_relative_path(relative_path),
    )
