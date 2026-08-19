"""Cache mémoire court thread-safe pour les résultats HealthProvider."""

from __future__ import annotations

import threading
import time
from typing import Generic, TypeVar

T = TypeVar("T")


class TtlCache(Generic[T]):
    """Cache TTL simple, thread-safe, sans persistence."""

    def __init__(self, *, ttl_seconds: float = 15.0) -> None:
        self._ttl = max(0.0, float(ttl_seconds))
        self._lock = threading.Lock()
        self._value: T | None = None
        self._expires_at: float = 0.0
        self._has_value = False

    @property
    def ttl_seconds(self) -> float:
        return self._ttl

    def get(self) -> T | None:
        with self._lock:
            if not self._has_value:
                return None
            if self._ttl > 0 and time.monotonic() >= self._expires_at:
                self._has_value = False
                self._value = None
                return None
            return self._value

    def set(self, value: T) -> None:
        with self._lock:
            self._value = value
            self._has_value = True
            self._expires_at = time.monotonic() + self._ttl if self._ttl > 0 else 0.0

    def clear(self) -> None:
        with self._lock:
            self._has_value = False
            self._value = None
            self._expires_at = 0.0

    def force_expire(self) -> None:
        """Expire immédiatement (tests / refresh forcé)."""
        with self._lock:
            self._expires_at = 0.0
            if self._ttl > 0:
                self._has_value = False
                self._value = None
