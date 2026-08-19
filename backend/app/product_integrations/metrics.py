"""Métriques product integrations — labels sans document_id (cardinalité)."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock

_LOCK = Lock()
_COUNTERS: dict[str, int] = defaultdict(int)


def incr(name: str, n: int = 1) -> None:
    with _LOCK:
        _COUNTERS[name] += n


def get(name: str) -> int:
    with _LOCK:
        return int(_COUNTERS.get(name, 0))


def snapshot() -> dict[str, int]:
    with _LOCK:
        return dict(_COUNTERS)


def reset_for_tests() -> None:
    with _LOCK:
        _COUNTERS.clear()
