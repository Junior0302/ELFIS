"""Client HTTP Supabase Storage (service role, serveur uniquement)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_SECRET_RE = re.compile(
    r"(?i)(authorization|apikey|bearer|service[_-]?role|eyJ[A-Za-z0-9_-]{10,})",
)


class SupabaseStorageError(RuntimeError):
    """Erreur Storage avec métadonnées sûres (pas de secrets)."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        classification: str | None = None,
        bucket: str | None = None,
        path: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.classification = classification
        self.bucket = bucket
        self.path = path
        self.endpoint = endpoint


def _mask_endpoint(url: str) -> str:
    """Masque l'hôte ; conserve chemin Storage sans secrets."""
    return re.sub(r"https?://[^/]+", "https://HOST", url or "")


def _clean_error_message(raw: str, *, max_len: int = 240) -> str:
    text = (raw or "").replace("\r", " ").replace("\n", " ").strip()
    text = _SECRET_RE.sub("[REDACTED]", text)
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _parse_supabase_error_body(response: httpx.Response) -> tuple[str | None, str]:
    """Retourne (error_code, cleaned_message) depuis le body Storage."""
    body_text = ""
    try:
        body_text = response.text or ""
    except Exception:
        body_text = ""
    code: str | None = None
    message = ""
    try:
        data: Any = response.json()
        if isinstance(data, dict):
            code_raw = data.get("error") or data.get("code") or data.get("statusCode")
            code = str(code_raw) if code_raw is not None else None
            message = str(
                data.get("message")
                or data.get("msg")
                or data.get("error_description")
                or ""
            )
    except (json.JSONDecodeError, ValueError):
        message = body_text
    if not message:
        message = body_text or response.reason_phrase or ""
    return code, _clean_error_message(message)


def _classify_http_status(status_code: int, message: str) -> str:
    lowered = (message or "").lower()
    if status_code in {401, 403}:
        if "jwt" in lowered or "invalid" in lowered or status_code == 401:
            return "authentication_failed"
        return "forbidden"
    if status_code == 404:
        if "bucket" in lowered:
            return "bucket_missing"
        return "not_found"
    if status_code == 413:
        return "payload_too_large"
    if status_code == 400:
        return "bad_request"
    if status_code >= 500:
        return "upstream_error"
    return f"http_{status_code}"


class SupabaseStorageClient:
    """Client minimal Storage API — n'expose jamais la clé service."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        service_role_key: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        raw_url = base_url if base_url is not None else settings.supabase_url
        self._base_url = settings._normalize_http_base_url(raw_url or "")
        self._key = (
            service_role_key
            if service_role_key is not None
            else settings.supabase_service_role_key
        )
        self._timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self._base_url and self._key)

    @property
    def base_url(self) -> str:
        return self._base_url

    def config_diagnostics(self) -> dict[str, Any]:
        """Métadonnées non secrètes pour health / diagnostics."""
        key = self._key or ""
        prefix = f"{key[:8]}..." if len(key) >= 8 else ("SET_SHORT" if key else "")
        return {
            "supabase_url_configured": bool(self._base_url),
            "service_role_configured": bool(self._key),
            "url_scheme_https": self._base_url.startswith("https://"),
            "url_has_storage_v1_suffix": "/storage/v1" in self._base_url.lower(),
            "key_length": len(key),
            "masked_key_prefix": prefix if key else "EMPTY",
        }

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._key}",
            "apikey": self._key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _raise_http_error(
        self,
        *,
        operation: str,
        response: httpx.Response,
        bucket: str,
        path: str,
        endpoint: str,
        content_type: str | None = None,
        content_size: int | None = None,
    ) -> None:
        error_code, cleaned = _parse_supabase_error_body(response)
        classification = _classify_http_status(response.status_code, cleaned)
        logger.error(
            f"supabase_storage_{operation}_failed",
            extra={
                "status_code": response.status_code,
                "error_code": error_code,
                "error_message": cleaned,
                "classification": classification,
                "endpoint": _mask_endpoint(endpoint),
                "bucket": bucket,
                "path": path,
                "content_type": content_type,
                "content_size": content_size,
                "timeout": self._timeout,
            },
        )
        raise SupabaseStorageError(
            f"Storage {operation} échoué (HTTP {response.status_code})",
            status_code=response.status_code,
            error_code=error_code,
            classification=classification,
            bucket=bucket,
            path=path,
            endpoint=_mask_endpoint(endpoint),
        )

    def _raise_transport_error(
        self,
        *,
        operation: str,
        exc: Exception,
        bucket: str,
        path: str,
        endpoint: str,
        content_type: str | None = None,
        content_size: int | None = None,
    ) -> None:
        if isinstance(exc, httpx.TimeoutException):
            classification = "timeout"
        elif isinstance(exc, httpx.InvalidURL):
            classification = "invalid_url"
        elif isinstance(exc, httpx.UnsupportedProtocol):
            classification = "invalid_url"
        elif isinstance(exc, httpx.ConnectError):
            classification = "project_unreachable"
        else:
            classification = "transport_error"
        cleaned = _clean_error_message(f"{type(exc).__name__}: {exc}")
        logger.error(
            f"supabase_storage_{operation}_transport_failed",
            extra={
                "status_code": None,
                "error_code": type(exc).__name__,
                "error_message": cleaned,
                "classification": classification,
                "endpoint": _mask_endpoint(endpoint),
                "bucket": bucket,
                "path": path,
                "content_type": content_type,
                "content_size": content_size,
                "timeout": self._timeout,
            },
        )
        raise SupabaseStorageError(
            f"Storage {operation} transport échoué ({classification})",
            status_code=None,
            error_code=type(exc).__name__,
            classification=classification,
            bucket=bucket,
            path=path,
            endpoint=_mask_endpoint(endpoint),
        ) from exc

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
        safe_path = (path or "").lstrip("/")
        url = f"{self._base_url}/storage/v1/object/{bucket}/{safe_path}"
        headers = self._headers(content_type)
        headers["x-upsert"] = "true" if upsert else "false"
        headers["cache-control"] = cache_control
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, content=content, headers=headers)
        except Exception as exc:
            self._raise_transport_error(
                operation="upload",
                exc=exc,
                bucket=bucket,
                path=safe_path,
                endpoint=url,
                content_type=content_type,
                content_size=len(content) if content is not None else None,
            )
            return
        if response.status_code >= 400:
            self._raise_http_error(
                operation="upload",
                response=response,
                bucket=bucket,
                path=safe_path,
                endpoint=url,
                content_type=content_type,
                content_size=len(content) if content is not None else None,
            )

    def delete_object(self, *, bucket: str, path: str) -> None:
        safe_path = (path or "").lstrip("/")
        url = f"{self._base_url}/storage/v1/object/{bucket}"
        headers = self._headers("application/json")
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.request(
                    "DELETE",
                    url,
                    headers=headers,
                    json={"prefixes": [safe_path]},
                )
        except Exception as exc:
            self._raise_transport_error(
                operation="delete",
                exc=exc,
                bucket=bucket,
                path=safe_path,
                endpoint=url,
            )
            return
        if response.status_code >= 400:
            self._raise_http_error(
                operation="delete",
                response=response,
                bucket=bucket,
                path=safe_path,
                endpoint=url,
                content_type="application/json",
            )

    def create_signed_url(
        self,
        *,
        bucket: str,
        path: str,
        expires_in: int = 3600,
    ) -> str:
        safe_path = (path or "").lstrip("/")
        url = f"{self._base_url}/storage/v1/object/sign/{bucket}/{safe_path}"
        headers = self._headers("application/json")
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    url,
                    headers=headers,
                    json={"expiresIn": expires_in},
                )
        except Exception as exc:
            self._raise_transport_error(
                operation="sign",
                exc=exc,
                bucket=bucket,
                path=safe_path,
                endpoint=url,
                content_type="application/json",
            )
            return ""
        if response.status_code >= 400:
            self._raise_http_error(
                operation="sign",
                response=response,
                bucket=bucket,
                path=safe_path,
                endpoint=url,
                content_type="application/json",
            )
        data = response.json()
        signed = data.get("signedURL") or data.get("signedUrl") or ""
        if not signed:
            raise SupabaseStorageError(
                "Réponse Storage sans signedURL",
                classification="bad_response",
                bucket=bucket,
                path=safe_path,
                endpoint=_mask_endpoint(url),
            )
        if signed.startswith("http"):
            return signed
        return f"{self._base_url}/storage/v1{signed}"

    def download_object(self, *, bucket: str, path: str) -> bytes:
        """Téléchargement serveur (service role) — jamais exposé au client."""
        safe_path = (path or "").lstrip("/")
        url = f"{self._base_url}/storage/v1/object/{bucket}/{safe_path}"
        headers = self._headers()
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, headers=headers)
        except Exception as exc:
            self._raise_transport_error(
                operation="download",
                exc=exc,
                bucket=bucket,
                path=safe_path,
                endpoint=url,
            )
            return b""
        if response.status_code >= 400:
            self._raise_http_error(
                operation="download",
                response=response,
                bucket=bucket,
                path=safe_path,
                endpoint=url,
            )
        return response.content

    def list_buckets(self) -> list[dict[str, Any]]:
        """Liste les buckets (diagnostic serveur)."""
        url = f"{self._base_url}/storage/v1/bucket"
        headers = self._headers()
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, headers=headers)
        except Exception as exc:
            self._raise_transport_error(
                operation="list_buckets",
                exc=exc,
                bucket="",
                path="",
                endpoint=url,
            )
            return []
        if response.status_code >= 400:
            self._raise_http_error(
                operation="list_buckets",
                response=response,
                bucket="",
                path="",
                endpoint=url,
            )
        data = response.json()
        return data if isinstance(data, list) else []
