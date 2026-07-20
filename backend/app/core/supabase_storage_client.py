"""Client HTTP Supabase Storage (service role, serveur uniquement)."""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseStorageClient:
    """Client minimal Storage API — n'expose jamais la clé service."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        service_role_key: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = (base_url if base_url is not None else settings.supabase_url).rstrip("/")
        self._key = (
            service_role_key
            if service_role_key is not None
            else settings.supabase_service_role_key
        )
        self._timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self._base_url and self._key)

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._key}",
            "apikey": self._key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def upload_object(
        self,
        *,
        bucket: str,
        path: str,
        content: bytes,
        content_type: str,
        upsert: bool = False,
        cache_control: str = "private, max-age=3600",
    ) -> None:
        url = f"{self._base_url}/storage/v1/object/{bucket}/{path}"
        headers = self._headers(content_type)
        headers["x-upsert"] = "true" if upsert else "false"
        headers["cache-control"] = cache_control
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(url, content=content, headers=headers)
        if response.status_code >= 400:
            logger.error(
                "supabase_storage_upload_failed",
                extra={"status_code": response.status_code, "bucket": bucket, "path": path},
            )
            raise RuntimeError(f"Upload Storage échoué (HTTP {response.status_code})")

    def delete_object(self, *, bucket: str, path: str) -> None:
        url = f"{self._base_url}/storage/v1/object/{bucket}"
        headers = self._headers("application/json")
        with httpx.Client(timeout=self._timeout) as client:
            response = client.request(
                "DELETE",
                url,
                headers=headers,
                json={"prefixes": [path]},
            )
        if response.status_code >= 400:
            logger.error(
                "supabase_storage_delete_failed",
                extra={"status_code": response.status_code, "bucket": bucket, "path": path},
            )
            raise RuntimeError(f"Suppression Storage échouée (HTTP {response.status_code})")

    def create_signed_url(
        self,
        *,
        bucket: str,
        path: str,
        expires_in: int = 3600,
    ) -> str:
        url = f"{self._base_url}/storage/v1/object/sign/{bucket}/{path}"
        headers = self._headers("application/json")
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                url,
                headers=headers,
                json={"expiresIn": expires_in},
            )
        if response.status_code >= 400:
            logger.error(
                "supabase_storage_sign_failed",
                extra={"status_code": response.status_code, "bucket": bucket, "path": path},
            )
            raise RuntimeError(f"URL signée échouée (HTTP {response.status_code})")
        data = response.json()
        signed = data.get("signedURL") or data.get("signedUrl") or ""
        if not signed:
            raise RuntimeError("Réponse Storage sans signedURL")
        if signed.startswith("http"):
            return signed
        return f"{self._base_url}/storage/v1{signed}"
