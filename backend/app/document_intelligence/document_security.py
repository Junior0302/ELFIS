"""Sécurité fichiers — Document Intelligence."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

from app.config import settings
from app.document_intelligence.document_exceptions import DocumentValidationError
from app.document_intelligence.document_types import (
    ALLOWED_MIME_TYPES_V1,
    EXTENSION_MIME,
    PREPARED_MIME_TYPES,
)

_NULL_RE = re.compile(r"[\x00]")


def assert_mime_allowed(mime_type: str | None, *, allow_prepared: bool = False) -> str:
    mime = (mime_type or "").strip().lower()
    allowed = set(ALLOWED_MIME_TYPES_V1)
    if allow_prepared:
        allowed |= set(PREPARED_MIME_TYPES)
    if mime not in allowed:
        raise DocumentValidationError(f"Type MIME non supporté: {mime or 'unknown'}")
    return mime


def assert_extension_matches_mime(filename: str | None, mime_type: str) -> None:
    name = Path(filename or "").name.lower()
    ext = Path(name).suffix
    expected = EXTENSION_MIME.get(ext)
    if expected and expected != mime_type:
        raise DocumentValidationError(
            f"Extension {ext} incohérente avec MIME {mime_type}"
        )


def assert_file_size(size: int) -> None:
    max_bytes = max(1024, int(settings.elfis_document_max_file_bytes))
    if size <= 0:
        raise DocumentValidationError("Fichier vide")
    if size > max_bytes:
        raise DocumentValidationError(f"Fichier trop volumineux (max {max_bytes} octets)")


def assert_safe_storage_path(storage_path: str) -> str:
    path = (storage_path or "").strip().replace("\\", "/")
    if not path or path.startswith("/") or ".." in path.split("/"):
        raise DocumentValidationError("Chemin storage invalide")
    if path.startswith("~") or ":" in path.split("/")[0]:
        raise DocumentValidationError("Chemin storage invalide")
    return path


def create_temp_file(*, suffix: str, content: bytes) -> Path:
    """Écrit dans un répertoire temporaire contrôlé (storage/tmp)."""
    base = settings.storage_path / "tmp" / "document_intelligence"
    base.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="di_", suffix=suffix, dir=str(base))
    path = Path(name)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return path
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def safe_unlink(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def assert_text_size(text: str) -> None:
    """
    Si le texte dépasse la limite : erreur explicite (pas de troncature silencieuse).
    Comportement V1 → requires_review / failed côté service.
    """
    raw = text.encode("utf-8")
    max_bytes = max(1024, int(settings.elfis_document_max_extracted_text_bytes))
    if len(raw) > max_bytes:
        raise DocumentValidationError(
            f"Texte extrait trop volumineux (max {max_bytes} octets, reçu {len(raw)})"
        )


def looks_like_binary(content: bytes) -> bool:
    if not content:
        return False
    sample = content[:4096]
    if b"\x00" in sample:
        return True
    # Ratio de non-texte
    textish = sum(1 for b in sample if 9 <= b <= 13 or 32 <= b <= 126 or b >= 128)
    return (textish / max(1, len(sample))) < 0.75
