"""Capacités déclaratives des StorageProvider."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StorageProviderCapabilities:
    """Les services consultent ces flags au lieu de supposer un FS local."""

    supports_atomic_move: bool = False
    supports_signed_urls: bool = False
    supports_range_requests: bool = False
    supports_direct_upload: bool = False
    supports_streaming_upload: bool = True
    # True = put_stream depuis un fichier local temporaire OS est le chemin recommandé
    prefers_local_temp_then_remote_put: bool = False
    supports_list_prefix: bool = False


LOCAL_CAPABILITIES = StorageProviderCapabilities(
    supports_atomic_move=True,
    supports_signed_urls=False,
    supports_range_requests=True,
    supports_direct_upload=False,
    supports_streaming_upload=True,
    prefers_local_temp_then_remote_put=False,
    supports_list_prefix=True,
)

SUPABASE_CAPABILITIES = StorageProviderCapabilities(
    supports_atomic_move=False,
    supports_signed_urls=True,
    supports_range_requests=False,  # non garanti via API simple
    supports_direct_upload=True,
    supports_streaming_upload=True,  # via file handle / chunks HTTP
    prefers_local_temp_then_remote_put=True,
    supports_list_prefix=True,
)

DISABLED_CAPABILITIES = StorageProviderCapabilities(
    supports_atomic_move=False,
    supports_signed_urls=False,
    supports_range_requests=False,
    supports_direct_upload=False,
    supports_streaming_upload=False,
    prefers_local_temp_then_remote_put=False,
    supports_list_prefix=False,
)
