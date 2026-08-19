"""Stockage objet pour ELFIS Vault (Supabase Storage V1).

Abstraction volontaire : pour basculer vers R2/S3 plus tard, remplacer
uniquement cette classe — routers et métier restent inchangés.
"""

from __future__ import annotations

import logging
import re
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.core.supabase_storage_client import SupabaseStorageClient, SupabaseStorageError
from app.schemas_vault import DOCUMENT_TYPE_CATEGORIES, VaultDocumentType
from app.services.vault.exceptions import VaultStorageError

logger = logging.getLogger(__name__)


def _safe_upload_extra(*, storage_path: str, bucket: str, content: bytes, exc: Exception) -> dict:
    """Métadonnées d'échec upload — jamais de secrets ni de contenu PDF."""
    extra: dict = {
        "path": storage_path,
        "bucket": bucket,
        "content_type": "application/pdf",
        "content_size": len(content) if content is not None else None,
    }
    if isinstance(exc, SupabaseStorageError):
        extra.update(
            {
                "status_code": exc.status_code,
                "error_code": exc.error_code,
                "classification": exc.classification,
                "endpoint": exc.endpoint,
                "error_message": str(exc)[:240],
            }
        )
    else:
        extra.update(
            {
                "status_code": getattr(exc, "status_code", None),
                "error_code": type(exc).__name__,
                "classification": "unexpected",
                "error_message": f"{type(exc).__name__}: {exc}"[:240],
            }
        )
    return extra


def sanitize_filename(filename: str) -> str:
    """Nettoie un nom de fichier pour un chemin Storage multi-tenant sûr."""
    name = Path(filename or "document.pdf").name
    name = name.replace("\\", "_").replace("/", "_")
    name = name.replace("..", "_")
    # Supprime accents
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    # Caractères de contrôle + spéciaux
    ascii_name = re.sub(r"[\x00-\x1f\x7f]", "", ascii_name)
    ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_name)
    ascii_name = re.sub(r"_+", "_", ascii_name).strip("._")
    if not ascii_name.lower().endswith(".pdf"):
        stem = ascii_name or "document"
        ascii_name = f"{stem}.pdf"
    if ascii_name == ".pdf":
        ascii_name = "document.pdf"
    # Limite longueur
    if len(ascii_name) > 180:
        stem = Path(ascii_name).stem[:160]
        ascii_name = f"{stem}.pdf"
    return ascii_name


def build_storage_path(
    *,
    organization_id: int,
    document_type: VaultDocumentType,
    original_filename: str,
    year: int | None = None,
) -> str:
    """Construit `entreprises/{org}/{year}/{category}/{safe}_{uuid}.pdf`."""
    category = DOCUMENT_TYPE_CATEGORIES.get(document_type, "autres")
    y = year or datetime.utcnow().year
    safe = sanitize_filename(original_filename)
    stem = Path(safe).stem
    short = uuid.uuid4().hex[:8]
    final_name = f"{stem}_{short}.pdf"
    return f"entreprises/{organization_id}/{y}/{category}/{final_name}"


class VaultStorageService:
    """Upload / delete / signed URL via Supabase Storage (bucket privé)."""

    def __init__(
        self,
        client: SupabaseStorageClient | None = None,
        bucket: str | None = None,
    ) -> None:
        self._client = client or SupabaseStorageClient()
        self._bucket = bucket or settings.elfis_vault_bucket

    def upload_pdf(self, *, storage_path: str, content: bytes) -> str:
        """Upload un PDF. upsert=false — ne remplace jamais silencieusement."""
        if not self._client.configured:
            logger.error(
                "vault_storage_not_configured",
                extra={
                    "bucket": self._bucket,
                    **(
                        self._client.config_diagnostics()
                        if hasattr(self._client, "config_diagnostics")
                        else {}
                    ),
                },
            )
            raise VaultStorageError("Stockage temporairement indisponible")
        safe_path = (storage_path or "").lstrip("/")
        try:
            self._client.upload_object(
                bucket=self._bucket,
                path=safe_path,
                content=content,
                content_type="application/pdf",
                upsert=False,
                cache_control="private, max-age=3600",
            )
        except Exception as exc:
            logger.error(
                "vault_storage_upload_error",
                extra=_safe_upload_extra(
                    storage_path=safe_path,
                    bucket=self._bucket,
                    content=content,
                    exc=exc,
                ),
            )
            raise VaultStorageError("Stockage temporairement indisponible") from exc
        return safe_path

    def delete_file(self, *, storage_path: str) -> None:
        """Suppression compensatoire après échec DB."""
        if not self._client.configured:
            logger.error("vault_storage_delete_skipped_not_configured", extra={"path": storage_path})
            return
        try:
            self._client.delete_object(bucket=self._bucket, path=storage_path)
        except Exception:
            logger.exception("vault_storage_compensating_delete_failed", extra={"path": storage_path})

    def create_signed_download_url(self, *, storage_path: str, expires_in: int = 3600) -> str:
        """Prêt pour l'endpoint de consultation futur — non appelé à l'archivage."""
        if not self._client.configured:
            raise VaultStorageError("Stockage temporairement indisponible")
        safe_path = (storage_path or "").lstrip("/")
        try:
            return self._client.create_signed_url(
                bucket=self._bucket,
                path=safe_path,
                expires_in=expires_in,
            )
        except Exception as exc:
            logger.error(
                "vault_storage_sign_error",
                extra=_safe_upload_extra(
                    storage_path=safe_path,
                    bucket=self._bucket,
                    content=b"",
                    exc=exc,
                ),
            )
            raise VaultStorageError("Stockage temporairement indisponible") from exc

    def download_bytes(self, *, storage_path: str) -> bytes:
        """Téléchargement interne serveur pour Document Intelligence / OCR."""
        if not self._client.configured:
            raise VaultStorageError("Stockage temporairement indisponible")
        safe_path = (storage_path or "").lstrip("/")
        try:
            return self._client.download_object(bucket=self._bucket, path=safe_path)
        except Exception as exc:
            logger.error(
                "vault_storage_download_error",
                extra=_safe_upload_extra(
                    storage_path=safe_path,
                    bucket=self._bucket,
                    content=b"",
                    exc=exc,
                ),
            )
            raise VaultStorageError("Stockage temporairement indisponible") from exc
