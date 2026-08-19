"""Mesure de performance simple."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from app.observability.metrics import metrics_registry


@contextmanager
def measure(metric_name: str, *, labels: dict[str, str] | None = None) -> Iterator[None]:
    started = time.perf_counter()
    try:
        yield
    finally:
        metrics_registry.observe(
            metric_name,
            (time.perf_counter() - started) * 1000,
            labels=labels,
        )
