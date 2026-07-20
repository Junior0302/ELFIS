"""Schémas métier notifications."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


FORBIDDEN_DATA_KEYS = frozenset(
    {
        "pdf",
        "pdf_bytes",
        "content",
        "api_key",
        "service_role_key",
        "jwt",
        "token",
        "password",
        "signed_url",
        "download_url",
        "authorization",
        "email_body",
        "iban",
        "bic",
    }
)


class NotificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: int
    user_id: int | None = None
    notification_type: str
    category: str
    severity: str = "info"
    template_name: str
    template_data: dict[str, Any] = Field(default_factory=dict)
    channels: list[str] = Field(default_factory=lambda: ["in_app"])
    action_url: str | None = None
    action_label: str | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    source_event_id: str | None = None
    correlation_id: str | None = None
    idempotency_key: str | None = None
    expires_at: datetime | None = None
    email_recipient: str | None = None

    @field_validator("template_data")
    @classmethod
    def _clean_template_data(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("template_data invalide")
        if len(value) > 40:
            raise ValueError("template_data trop volumineux")
        bad = {str(k).lower() for k in value} & FORBIDDEN_DATA_KEYS
        if bad:
            raise ValueError(f"clés interdites: {sorted(bad)}")
        return value


class RenderedNotification(BaseModel):
    title: str
    message: str
    email_subject: str | None = None
    email_text: str | None = None
    email_html: str | None = None
    action_url: str | None = None
    action_label: str | None = None
    severity: str | None = None


class DeliveryResult(BaseModel):
    channel: str
    status: str
    recipient: str | None = None
    provider_message_id: str | None = None


class NotificationResult(BaseModel):
    notification_id: str
    created: bool
    status: str
    deliveries: list[DeliveryResult] = Field(default_factory=list)


class NotificationOut(BaseModel):
    notification_id: str
    notification_type: str
    category: str
    title: str
    message: str
    severity: str
    status: str
    action_url: str | None = None
    action_label: str | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    created_at: datetime | None = None
    read_at: datetime | None = None
