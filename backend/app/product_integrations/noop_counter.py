"""Compteur thread-safe pour instrumenter NoopDocumentBridge en tests."""

from __future__ import annotations

from threading import Lock

_LOCK = Lock()
_CALLS = 0


def reset_noop_deliver_calls() -> None:
    global _CALLS
    with _LOCK:
        _CALLS = 0


def incr_noop_deliver_calls() -> int:
    global _CALLS
    with _LOCK:
        _CALLS += 1
        return _CALLS


def get_noop_deliver_calls() -> int:
    with _LOCK:
        return _CALLS
