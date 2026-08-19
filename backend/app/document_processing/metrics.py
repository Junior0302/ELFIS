"""Compteurs processing — bornés, sans contenu documentaire."""

from __future__ import annotations

import logging
from threading import Lock

logger = logging.getLogger(__name__)

_lock = Lock()
_counters: dict[str, int] = {
    "jobs_created": 0,
    "jobs_completed": 0,
    "jobs_failed": 0,
    "jobs_cancelled": 0,
    "steps_completed": 0,
    "steps_failed": 0,
    "leases_recovered": 0,
}


def incr(name: str, amount: int = 1) -> None:
    with _lock:
        if name in _counters:
            _counters[name] = _counters[name] + amount


def snapshot() -> dict[str, int]:
    with _lock:
        return dict(_counters)


def reset_for_tests() -> None:
    with _lock:
        for key in _counters:
            _counters[key] = 0
