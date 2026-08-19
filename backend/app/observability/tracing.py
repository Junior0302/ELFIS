"""Tracing léger V1 — spans locaux sans dépendance OTel."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Iterator

from app.observability.request_context import get_correlation_id, get_request_id


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[dict[str, Any]]:
    started = time.perf_counter()
    data: dict[str, Any] = {
        "name": name,
        "request_id": get_request_id(),
        "correlation_id": get_correlation_id(),
        "attributes": attributes,
    }
    try:
        yield data
        data["status"] = "ok"
    except Exception as exc:
        data["status"] = "error"
        data["error"] = type(exc).__name__
        raise
    finally:
        data["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)
