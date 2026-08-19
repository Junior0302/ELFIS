"""Métriques OCR bornées — aucun texte."""

from __future__ import annotations

from threading import Lock

_lock = Lock()
_counters: dict[str, int] = {
    "ocr_started": 0,
    "ocr_completed": 0,
    "ocr_failed": 0,
    "ocr_text_accessed": 0,
    "ocr_artifacts_created": 0,
}


def incr(name: str, amount: int = 1) -> None:
    with _lock:
        if name in _counters:
            _counters[name] += amount


def snapshot() -> dict[str, int]:
    with _lock:
        return dict(_counters)
