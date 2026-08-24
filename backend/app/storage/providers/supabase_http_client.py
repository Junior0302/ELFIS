"""Client HTTP isolé Supabase Storage (document registry) — injectable / mockable.

Choix technique RC2.4 étape 4 :
- httpx (déjà utilisé par Vault) plutôt que le SDK JS/Python lourd ;
- upload depuis un fichier temporaire OS (streaming file handle) ;
- download via response.iter_bytes (pas de .content complet) ;
- service role uniquement serveur — jamais loguée.
"""

from __future__ import annotations

import logging
import time
from typing import BinaryIO, Iterator
from uuid import uuid4

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseStorageHttpClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        service_role_key: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = (
            base_url
            if base_url is not None
            else (getattr(settings, "supabase_storage_url", None) or settings.supabase_url or "")
        ).rstrip("/")
        self._key = (
            service_role_key
            if service_role_key is not None
            else (
                getattr(settings, "supabase_storage_service_role_key", None)
                or settings.supabase_service_role_key
                or ""
            )
        )
        self._timeout = float(
            timeout
            if timeout is not None
            else getattr(settings, "supabase_storage_request_timeout_seconds", 60) or 60
        )
        self._max_retries = int(
            max_retries
            if max_retries is not None
            else getattr(settings, "supabase_storage_max_retries", 2) or 2
        )
        self._transport = transport
        self._client: httpx.Client | None = None

    @property
    def configured(self) -> bool:
        return bool(self._base_url and self._key)

    def _ensure_client(self) -> httpx.Client:
        if self._client is None:
            kwargs: dict = {"timeout": self._timeout}
            if self._transport is not None:
                kwargs["transport"] = self._transport
            self._client = httpx.Client(**kwargs)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._key}",
            "apikey": self._key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        client = self._ensure_client()
        last_exc: Exception | None = None
        attempts = max(1, self._max_retries + 1)
        for attempt in range(attempts):
            try:
                response = client.request(method, url, **kwargs)
                if response.status_code in {429, 500, 502, 503, 504} and attempt < attempts - 1:
                    time.sleep(min(2**attempt * 0.2, 2.0))
                    continue
                return response
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt < attempts - 1:
                    time.sleep(min(2**attempt * 0.2, 2.0))
                    continue
                raise
        if last_exc:
            raise last_exc
        raise RuntimeError("request_failed")

    def upload_bytes(
        self,
        *,
        bucket: str,
        path: str,
        content: bytes,
        content_type: str,
        upsert: bool = False,
    ) -> None:
        url = f"{self._base_url}/storage/v1/object/{bucket}/{path}"
        headers = self._headers(content_type)
        headers["x-upsert"] = "true" if upsert else "false"
        headers["cache-control"] = "private, no-store"
        response = self._request("POST", url, content=content, headers=headers)
        if response.status_code >= 400:
            logger.error(
                "supabase_doc_upload_failed",
                extra={"status_code": response.status_code, "bucket": bucket},
            )
            raise RuntimeError(f"upload_failed:{response.status_code}")

    def upload_fileobj(
        self,
        *,
        bucket: str,
        path: str,
        fileobj: BinaryIO,
        content_type: str,
        upsert: bool = False,
    ) -> None:
        """Upload depuis un file-like — httpx lit le flux sans charger tout en RAM côté app.

        Note : httpx peut bufferiser selon transport ; on évite fileobj.read() complet.
        """
        url = f"{self._base_url}/storage/v1/object/{bucket}/{path}"
        headers = self._headers(content_type)
        headers["x-upsert"] = "true" if upsert else "false"
        headers["cache-control"] = "private, no-store"

        def _iter() -> Iterator[bytes]:
            while True:
                chunk = fileobj.read(65536)
                if not chunk:
                    break
                yield chunk

        response = self._request("POST", url, content=_iter(), headers=headers)
        if response.status_code >= 400:
            logger.error(
                "supabase_doc_upload_stream_failed",
                extra={"status_code": response.status_code, "bucket": bucket},
            )
            raise RuntimeError(f"upload_failed:{response.status_code}")

    def download_stream(self, *, bucket: str, path: str) -> httpx.Response:
        url = f"{self._base_url}/storage/v1/object/{bucket}/{path}"
        client = self._ensure_client()
        request = client.build_request("GET", url, headers=self._headers())
        response = client.send(request, stream=True)
        if response.status_code >= 400:
            response.close()
            logger.error(
                "supabase_doc_download_failed",
                extra={"status_code": response.status_code, "bucket": bucket},
            )
            raise RuntimeError(f"download_failed:{response.status_code}")
        return response

    def download_bytes(self, *, bucket: str, path: str) -> bytes:
        url = f"{self._base_url}/storage/v1/object/{bucket}/{path}"
        response = self._request("GET", url, headers=self._headers())
        if response.status_code >= 400:
            raise RuntimeError(f"download_failed:{response.status_code}")
        return response.content

    def delete_object(self, *, bucket: str, path: str) -> int:
        url = f"{self._base_url}/storage/v1/object/{bucket}"
        response = self._request(
            "DELETE",
            url,
            headers=self._headers("application/json"),
            json={"prefixes": [path]},
        )
        return response.status_code

    def object_info(self, *, bucket: str, path: str) -> dict | None:
        """HEAD-like via download headers or list — utilise GET stream minimal."""
        # Storage API : info via list with search
        parent = "/".join(path.split("/")[:-1]) if "/" in path else ""
        name = path.split("/")[-1]
        url = f"{self._base_url}/storage/v1/object/list/{bucket}"
        response = self._request(
            "POST",
            url,
            headers=self._headers("application/json"),
            json={"prefix": parent, "search": name, "limit": 20},
        )
        if response.status_code >= 400:
            return None
        items = response.json() if response.content else []
        if not isinstance(items, list):
            return None
        for item in items:
            if isinstance(item, dict) and item.get("name") == name:
                return item
            # nested path full name
            if isinstance(item, dict) and item.get("name") == path:
                return item
        return None

    def create_signed_url(self, *, bucket: str, path: str, expires_in: int = 300) -> str:
        url = f"{self._base_url}/storage/v1/object/sign/{bucket}/{path}"
        response = self._request(
            "POST",
            url,
            headers=self._headers("application/json"),
            json={"expiresIn": expires_in},
        )
        if response.status_code >= 400:
            raise RuntimeError(f"sign_failed:{response.status_code}")
        data = response.json()
        signed = data.get("signedURL") or data.get("signedUrl") or ""
        if not signed:
            raise RuntimeError("sign_empty")
        if signed.startswith("http"):
            return signed
        return f"{self._base_url}/storage/v1{signed}"

    def list_prefix(self, *, bucket: str, prefix: str, limit: int = 100) -> list[dict]:
        url = f"{self._base_url}/storage/v1/object/list/{bucket}"
        response = self._request(
            "POST",
            url,
            headers=self._headers("application/json"),
            json={"prefix": prefix, "limit": max(1, min(limit, 1000))},
        )
        if response.status_code >= 400:
            return []
        data = response.json() if response.content else []
        return data if isinstance(data, list) else []


class SupabaseStorageClientFactory:
    """Factory légère — un client réutilisable par provider instance."""

    @staticmethod
    def build(**kwargs) -> SupabaseStorageHttpClient:
        return SupabaseStorageHttpClient(**kwargs)

    @staticmethod
    def probe_id() -> str:
        return f"health-probes/{uuid4().hex}.probe"
