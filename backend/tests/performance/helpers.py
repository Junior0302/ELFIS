"""Helpers Phase F — performance et concurrence."""

from __future__ import annotations

import os
import statistics
import time
from typing import Any, Callable


def performance_enabled() -> bool:
    return os.getenv("ELFIS_PERFORMANCE_TESTS_ENABLED", "true").lower() in {"1", "true", "yes"}


def concurrency_enabled() -> bool:
    """Tests lourds / multi-thread — off par défaut hors campagne Phase F."""
    return os.getenv("ELFIS_CONCURRENCY_TESTS_ENABLED", "false").lower() in {"1", "true", "yes"}


def is_postgres_url(url: str | None = None) -> bool:
    raw = (url or os.getenv("ELFIS_PERFORMANCE_DATABASE_URL") or os.getenv("DATABASE_URL") or "").lower()
    return raw.startswith("postgresql") or raw.startswith("postgres://")


def refuse_production_url(url: str) -> None:
    lowered = (url or "").lower()
    if any(x in lowered for x in ("prod", "production", "render.com", "neon.tech/prod")):
        if os.getenv("ELFIS_PERFORMANCE_ALLOW_REMOTE", "").lower() not in {"1", "true", "yes"}:
            raise RuntimeError(
                "URL suspecte de production refusée. "
                "Définir ELFIS_PERFORMANCE_ALLOW_REMOTE=true pour forcer (non recommandé)."
            )


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def measure_latencies(fn: Callable[[], Any], *, rounds: int = 20, warmup: int = 2) -> dict[str, Any]:
    for _ in range(warmup):
        fn()
    samples: list[float] = []
    errors = 0
    last: Any = None
    for _ in range(rounds):
        t0 = time.perf_counter()
        try:
            last = fn()
        except Exception:
            errors += 1
            continue
        samples.append((time.perf_counter() - t0) * 1000.0)
    return {
        "n": len(samples),
        "errors": errors,
        "median_ms": statistics.median(samples) if samples else None,
        "p95_ms": percentile(samples, 95) if samples else None,
        "p99_ms": percentile(samples, 99) if samples else None,
        "max_ms": max(samples) if samples else None,
        "last": last,
    }
