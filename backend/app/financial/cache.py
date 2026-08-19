"""Cache TTL par organisation pour les calculs du Financial Engine.

Les agrégats sont recalculés au plus toutes les ``financial_cache_ttl_seconds``
secondes (défaut 60 s) ; ``refresh=True`` sur l'API force le recalcul.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from app.config import settings


class KeyedTtlCache:
    """Cache TTL thread-safe indexé par clé (organization_id)."""

    def __init__(self, *, ttl_seconds: float | None = None) -> None:
        self._ttl = float(
            ttl_seconds
            if ttl_seconds is not None
            else getattr(settings, "financial_cache_ttl_seconds", 60)
        )
        self._lock = threading.Lock()
        self._values: dict[Any, tuple[float, Any]] = {}

    @property
    def ttl_seconds(self) -> float:
        return self._ttl

    def get(self, key: Any) -> Any | None:
        with self._lock:
            entry = self._values.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if self._ttl > 0 and time.monotonic() >= expires_at:
                self._values.pop(key, None)
                return None
            return value

    def set(self, key: Any, value: Any) -> None:
        with self._lock:
            self._values[key] = (time.monotonic() + self._ttl, value)

    def invalidate(self, key: Any) -> None:
        with self._lock:
            self._values.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._values.clear()


# Cache partagé des snapshots financiers (process-local)
snapshot_cache = KeyedTtlCache()

# Dernières empreintes publiées (détection de changement pour les événements)
_last_hashes: dict[str, str] = {}
_hash_lock = threading.Lock()


def value_changed(key: str, fingerprint: str) -> bool:
    """True si l'empreinte diffère de la dernière connue (et la mémorise)."""
    with _hash_lock:
        if _last_hashes.get(key) == fingerprint:
            return False
        _last_hashes[key] = fingerprint
        return True


def reset_change_tracking() -> None:
    with _hash_lock:
        _last_hashes.clear()
