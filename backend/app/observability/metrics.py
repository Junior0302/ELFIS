"""Registre de métriques mémoire — interface compatible Prometheus JSON."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _Counter:
    value: float = 0.0


@dataclass
class _Histogram:
    count: int = 0
    sum: float = 0.0
    samples: list[float] = field(default_factory=list)


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, dict[tuple[tuple[str, str], ...], _Counter]] = defaultdict(dict)
        self._histograms: dict[str, dict[tuple[tuple[str, str], ...], _Histogram]] = defaultdict(dict)
        self._gauges: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(dict)
        self.started_at = time.time()

    @staticmethod
    def _label_key(labels: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
        if not labels:
            return ()
        return tuple(sorted((str(k), str(v)[:64]) for k, v in labels.items()))

    def incr(self, name: str, *, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        key = self._label_key(labels)
        with self._lock:
            bucket = self._counters[name]
            if key not in bucket:
                bucket[key] = _Counter()
            bucket[key].value += value

    def observe(self, name: str, value: float, *, labels: dict[str, str] | None = None) -> None:
        key = self._label_key(labels)
        with self._lock:
            bucket = self._histograms[name]
            if key not in bucket:
                bucket[key] = _Histogram()
            h = bucket[key]
            h.count += 1
            h.sum += value
            if len(h.samples) < 200:
                h.samples.append(value)

    def set_gauge(self, name: str, value: float, *, labels: dict[str, str] | None = None) -> None:
        key = self._label_key(labels)
        with self._lock:
            self._gauges[name][key] = value

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = {
                name: [
                    {"labels": dict(labels), "value": c.value}
                    for labels, c in series.items()
                ]
                for name, series in self._counters.items()
            }
            histograms = {
                name: [
                    {
                        "labels": dict(labels),
                        "count": h.count,
                        "sum": h.sum,
                        "avg": (h.sum / h.count) if h.count else 0.0,
                    }
                    for labels, h in series.items()
                ]
                for name, series in self._histograms.items()
            }
            gauges = {
                name: [{"labels": dict(labels), "value": v} for labels, v in series.items()]
                for name, series in self._gauges.items()
            }
        return {
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "counters": counters,
            "histograms": histograms,
            "gauges": gauges,
        }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()
            self.started_at = time.time()


metrics_registry = MetricsRegistry()
