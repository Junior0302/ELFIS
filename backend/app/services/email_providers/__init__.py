"""Abstraction minimale des fournisseurs d’e-mail plateforme (MAIL-1)."""

from app.services.email_providers.platform import PlatformEmailProvider
from app.services.email_providers.types import (
    DEFAULT_SENDER_NAME,
    EmailProvider,
    EmailProviderError,
    ProviderSendResult,
)

__all__ = [
    "DEFAULT_SENDER_NAME",
    "EmailProvider",
    "EmailProviderError",
    "PlatformEmailProvider",
    "ProviderSendResult",
]
