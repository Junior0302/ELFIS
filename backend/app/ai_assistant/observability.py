"""Observabilité + cache intelligent des tours d'assistant."""

from __future__ import annotations

import hashlib
import threading
import time
from typing import Any

from sqlalchemy.orm import Session

from app.ai_assistant.models import ElfisAssistantRun
from app.ai_assistant.types import AssistantRunMetrics
from app.ai.ai_usage import estimate_cost
from app.config import settings


class AssistantCache:
    """Cache TTL des réponses déterministes (même question + org + fingerprint données)."""

    def __init__(self, *, ttl_seconds: float | None = None):
        self._ttl = float(
            ttl_seconds
            if ttl_seconds is not None
            else getattr(settings, "ai_assistant_cache_ttl_seconds", 45)
        )
        self._lock = threading.Lock()
        self._store: dict[str, tuple[float, Any]] = {}

    def key(self, organization_id: int, question: str, data_fingerprint: str) -> str:
        raw = f"{organization_id}|{question.strip().lower()}|{data_fingerprint}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires, value = entry
            if self._ttl > 0 and time.monotonic() >= expires:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


response_cache = AssistantCache()


def persist_run(
    db: Session,
    *,
    organization_id: int,
    user_id: int | None,
    question: str,
    metrics: AssistantRunMetrics,
) -> ElfisAssistantRun:
    run = ElfisAssistantRun(
        organization_id=organization_id,
        user_id=user_id,
        question_preview=(question or "")[:200],
        latency_ms=metrics.latency_ms,
        llm_latency_ms=metrics.llm_latency_ms,
        llm_called=1 if metrics.llm_called else 0,
        input_tokens=metrics.input_tokens,
        output_tokens=metrics.output_tokens,
        estimated_cost=metrics.estimated_cost,
        tools_called=list(metrics.tools_called),
        cache_hit=1 if metrics.cache_hit else 0,
        error=metrics.error,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def cost_from_tokens(provider: str, model: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    cost = estimate_cost(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    return float(cost) if cost is not None else None
