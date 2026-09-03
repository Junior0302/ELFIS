"""Rate limiting mémoire V1 — abstraction prête pour Redis."""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from app.security.security_config import rate_limit_for
from app.security.security_types import RateLimitCategory


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    category: str


class RateLimitBackend(Protocol):
    def hit(self, key: str, *, limit: int, window_s: float) -> RateLimitResult: ...


class MemoryRateLimitBackend:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str, *, limit: int, window_s: float = 60.0) -> RateLimitResult:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets[key]
            while bucket and now - bucket[0] > window_s:
                bucket.popleft()
            if len(bucket) >= limit:
                oldest = bucket[0]
                retry = max(1, int(window_s - (now - oldest)) + 1)
                cat = key.split(":", 1)[0] if ":" in key else "default"
                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after_seconds=retry,
                    category=cat,
                )
            bucket.append(now)
            cat = key.split(":", 1)[0] if ":" in key else "default"
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=max(0, limit - len(bucket)),
                retry_after_seconds=0,
                category=cat,
            )

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


_default_backend = MemoryRateLimitBackend()


def get_rate_limit_backend() -> MemoryRateLimitBackend:
    return _default_backend


def hash_ip(ip: str | None) -> str:
    raw = (ip or "unknown").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def build_rate_key(
    category: RateLimitCategory | str,
    *,
    ip: str | None = None,
    user_id: int | None = None,
    organization_id: int | None = None,
    route: str | None = None,
) -> str:
    cat = category.value if isinstance(category, RateLimitCategory) else str(category)
    parts = [cat]
    if user_id is not None:
        parts.append(f"u{user_id}")
    if organization_id is not None:
        parts.append(f"o{organization_id}")
    if ip:
        parts.append(f"ip{hash_ip(ip)}")
    if route:
        parts.append(f"r{route[:80]}")
    return ":".join(parts)


def check_rate_limit(
    category: RateLimitCategory | str,
    *,
    ip: str | None = None,
    user_id: int | None = None,
    organization_id: int | None = None,
    route: str | None = None,
    backend: MemoryRateLimitBackend | None = None,
) -> RateLimitResult:
    limit = rate_limit_for(category)
    key = build_rate_key(
        category,
        ip=ip,
        user_id=user_id,
        organization_id=organization_id,
        route=route,
    )
    store = backend or get_rate_limit_backend()
    result = store.hit(key, limit=limit, window_s=60.0)
    result.category = category.value if isinstance(category, RateLimitCategory) else str(category)
    return result


# Préfixes → catégories (routes sensibles)
ROUTE_CATEGORY_PREFIXES: tuple[tuple[str, RateLimitCategory], ...] = (
    ("/api/auth/login", RateLimitCategory.AUTH),
    ("/api/auth/register", RateLimitCategory.AUTH),
    ("/api/auth/firebase", RateLimitCategory.AUTH),
    ("/api/vault", RateLimitCategory.UPLOAD),
    ("/api/documents", RateLimitCategory.UPLOAD),
    ("/api/ai", RateLimitCategory.AI),
    ("/api/elfis-ai", RateLimitCategory.AI),
    ("/api/search", RateLimitCategory.SEARCH),
    ("/api/notifications", RateLimitCategory.EMAIL),
    ("/api/subscriptions/checkout", RateLimitCategory.BILLING),
    ("/api/subscriptions/portal", RateLimitCategory.BILLING),
    ("/api/billing", RateLimitCategory.BILLING),
    ("/api/platform", RateLimitCategory.PLATFORM_ADMIN),
    ("/api/subscriptions/webhook", RateLimitCategory.WEBHOOK),
    ("/api/webhooks/stripe", RateLimitCategory.WEBHOOK),
    ("/api/banking/connectors/bridge/webhook", RateLimitCategory.WEBHOOK),
)


def category_for_path(path: str) -> RateLimitCategory | None:
    """None = pas de rate limit catégorie (hors default global optionnel)."""
    for prefix, cat in ROUTE_CATEGORY_PREFIXES:
        if path.startswith(prefix):
            return cat
    return None
