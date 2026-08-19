"""Cache mémoire court des permissions effectives par utilisateur."""

from __future__ import annotations

import threading
import time
from typing import Generic, TypeVar

T = TypeVar("T")


class PermissionCache(Generic[T]):
    """Cache TTL thread-safe. ttl<=0 désactive le cache (tests)."""

    def __init__(self, *, ttl_seconds: float = 30.0) -> None:
        self._ttl = float(ttl_seconds)
        self._lock = threading.Lock()
        self._store: dict[str, tuple[float, T]] = {}

    @property
    def enabled(self) -> bool:
        return self._ttl > 0

    def get(self, key: str) -> T | None:
        if not self.enabled:
            return None
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expires_at, value = item
            if time.monotonic() >= expires_at:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: T) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._store[key] = (time.monotonic() + self._ttl, value)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def invalidate_user(self, user_id: int) -> None:
        self.invalidate(f"user:{user_id}")

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# Singleton process — désactivable via ttl=0 en tests
effective_permissions_cache: PermissionCache[frozenset[str]] = PermissionCache(ttl_seconds=30.0)


def configure_permission_cache(*, ttl_seconds: float) -> None:
    global effective_permissions_cache
    effective_permissions_cache = PermissionCache(ttl_seconds=ttl_seconds)
