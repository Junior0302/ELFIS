"""Métriques bornées extraction (compteurs, jamais de valeurs)."""

from __future__ import annotations

from collections import defaultdict

_COUNTS: dict[str, int] = defaultdict(int)


def incr(name: str, n: int = 1) -> None:
    _COUNTS[name] += n


def snapshot() -> dict[str, int]:
    return dict(_COUNTS)


def reset_for_tests() -> None:
    _COUNTS.clear()
