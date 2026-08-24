"""Registry des providers de stockage."""

from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.storage.providers.disabled_storage_provider import DisabledStorageProvider
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_exceptions import StorageProviderError
from app.storage.storage_provider import StorageProvider
from app.storage.storage_types import StorageProviderName


def build_storage_provider(name: str | None = None) -> StorageProvider:
    raw = (name or getattr(settings, "storage_provider", "local") or "local").strip().lower()
    if raw == StorageProviderName.DISABLED.value:
        return DisabledStorageProvider()
    if raw == StorageProviderName.LOCAL.value:
        return LocalStorageProvider()
    if raw == StorageProviderName.SUPABASE.value:
        from app.storage.providers.supabase_storage_provider import SupabaseStorageProvider

        try:
            return SupabaseStorageProvider()
        except StorageProviderError:
            # Config incomplète → disabled sûr (pas de crash au boot)
            return DisabledStorageProvider()
    return DisabledStorageProvider()


@lru_cache(maxsize=1)
def get_default_storage_provider() -> StorageProvider:
    return build_storage_provider()


def clear_storage_provider_cache() -> None:
    get_default_storage_provider.cache_clear()


def get_provider_info() -> dict:
    """Métadonnées non secrètes pour admin / health."""
    configured = (getattr(settings, "storage_provider", "local") or "local").strip().lower()
    provider = build_storage_provider()
    caps = provider.capabilities
    return {
        "configured_provider": configured,
        "active_provider": provider.name,
        "capabilities": {
            "supports_atomic_move": caps.supports_atomic_move,
            "supports_signed_urls": caps.supports_signed_urls,
            "supports_range_requests": caps.supports_range_requests,
            "prefers_local_temp_then_remote_put": caps.prefers_local_temp_then_remote_put,
        },
        "download_mode": getattr(settings, "storage_download_mode", "proxy"),
        "supabase_bucket_configured": bool(getattr(settings, "supabase_storage_bucket", "")),
        "supabase_url_configured": bool(
            (getattr(settings, "supabase_storage_url", None) or settings.supabase_url or "").strip()
        ),
    }
