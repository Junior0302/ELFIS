"""Contexte d'audit — champs optionnels (acteur, org, corrélation, etc.)."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from app.observability import request_context as req_ctx


@dataclass
class AuditContext:
    actor_user_id: int | None = None
    actor_email: str | None = None
    organization_id: int | None = None
    product: str | None = None
    service: str | None = None
    permissions: frozenset[str] = field(default_factory=frozenset)
    request_id: str | None = None
    correlation_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    session_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_request_context(
        cls,
        *,
        actor_user_id: int | None = None,
        actor_email: str | None = None,
        organization_id: int | None = None,
        product: str | None = None,
        service: str | None = None,
        permissions: frozenset[str] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> AuditContext:
        return cls(
            actor_user_id=actor_user_id if actor_user_id is not None else req_ctx.get_user_id(),
            actor_email=actor_email,
            organization_id=(
                organization_id if organization_id is not None else req_ctx.get_organization_id()
            ),
            product=product,
            service=service,
            permissions=permissions or frozenset(),
            request_id=req_ctx.get_request_id(),
            correlation_id=req_ctx.get_correlation_id(),
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
        )

    def merge(self, other: AuditContext | None) -> AuditContext:
        if other is None:
            return self
        return AuditContext(
            actor_user_id=other.actor_user_id if other.actor_user_id is not None else self.actor_user_id,
            actor_email=other.actor_email if other.actor_email is not None else self.actor_email,
            organization_id=(
                other.organization_id if other.organization_id is not None else self.organization_id
            ),
            product=other.product if other.product is not None else self.product,
            service=other.service if other.service is not None else self.service,
            permissions=other.permissions or self.permissions,
            request_id=other.request_id if other.request_id is not None else self.request_id,
            correlation_id=(
                other.correlation_id if other.correlation_id is not None else self.correlation_id
            ),
            ip_address=other.ip_address if other.ip_address is not None else self.ip_address,
            user_agent=other.user_agent if other.user_agent is not None else self.user_agent,
            session_id=other.session_id if other.session_id is not None else self.session_id,
            extra={**self.extra, **other.extra},
        )


_audit_context: ContextVar[AuditContext | None] = ContextVar("elfis_audit_context", default=None)


def bind_audit_context(ctx: AuditContext) -> None:
    _audit_context.set(ctx)


def get_audit_context() -> AuditContext | None:
    return _audit_context.get()


def clear_audit_context() -> None:
    _audit_context.set(None)


def current_audit_context() -> AuditContext:
    bound = get_audit_context()
    if bound is not None:
        return bound
    return AuditContext.from_request_context()
