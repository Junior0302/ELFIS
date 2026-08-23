from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

DEFAULT_SENDER_NAME = "ELFIS Core"

# Plus petit index = plus utile pour l’utilisateur / l’admin (MAIL-1).
ERROR_PRIORITY: tuple[str, ...] = (
    "sender_not_configured",
    "missing_api_key",
    "provider_not_configured",
    "sender_not_verified",
    "authentication_failed",
    "recipient_missing",
    "recipient_invalid",
    "rate_limit",
    "timeout",
    "provider_unreachable",
    "delivery_failed",
)

FALLBACK_COMPATIBLE_ERRORS = frozenset(
    {
        "authentication_failed",
        "sender_not_verified",
        "rate_limit",
        "timeout",
        "provider_unreachable",
        "delivery_failed",
    }
)

USER_SAFE_MESSAGES: dict[str, str] = {
    "authentication_failed": (
        "Le service d’envoi ELFIS n’a pas pu s’authentifier auprès du fournisseur de messagerie."
    ),
    "sender_not_configured": "L’expéditeur de la plateforme n’est pas configuré.",
    "sender_not_verified": (
        "L’expéditeur plateforme n’est pas validé chez le fournisseur de messagerie."
    ),
    "missing_api_key": "Le service d’envoi ELFIS n’est pas correctement configuré.",
    "missing_smtp_credentials": "Le service d’envoi ELFIS n’est pas correctement configuré.",
    "provider_not_configured": "Le service d’envoi ELFIS n’est pas configuré.",
    "recipient_missing": "Ajoutez une adresse e-mail au destinataire avant l’envoi.",
    "recipient_invalid": "L’adresse e-mail du destinataire est invalide.",
    "rate_limit": "Le fournisseur de messagerie limite temporairement les envois. Réessayez plus tard.",
    "timeout": "Délai dépassé lors de l’envoi. Réessayez dans quelques minutes.",
    "provider_unreachable": "Le fournisseur de messagerie est injoignable. Réessayez plus tard.",
    "delivery_failed": (
        "L’e-mail n’a pas pu être envoyé. Aucun message n’a été remis au destinataire."
    ),
    "attachment_missing": "Le document PDF n’a pas pu être généré. Veuillez réessayer.",
}


def user_safe_message(error_code: str) -> str:
    return USER_SAFE_MESSAGES.get(error_code) or USER_SAFE_MESSAGES["delivery_failed"]


def error_rank(error_code: str) -> int:
    try:
        return ERROR_PRIORITY.index(error_code)
    except ValueError:
        return len(ERROR_PRIORITY)


def pick_preferred_error(*codes: str) -> str:
    """Choisit le code le plus actionnable. En cas d’égalité, le premier gagne (API avant SMTP)."""
    usable = [code for code in codes if code]
    if not usable:
        return "delivery_failed"
    return min(usable, key=lambda code: (error_rank(code), usable.index(code)))


@dataclass(frozen=True)
class ProviderSendResult:
    success: bool
    provider: str
    transport: str
    provider_message_id: str = ""
    sender_email: str = ""
    sender_name: str = ""
    error_code: str = ""
    safe_error_detail: str = ""
    used_fallback: bool = False
    http_status: int | None = None
    smtp_code: str = ""


class EmailProviderError(RuntimeError):
    """Échec fournisseur — message sûr (jamais de secret)."""

    def __init__(
        self,
        error_code: str,
        *,
        transport: str = "",
        http_status: int | None = None,
        smtp_code: str = "",
        used_fallback: bool = False,
        safe_detail: str = "",
    ) -> None:
        self.error_code = error_code
        self.transport = transport
        self.http_status = http_status
        self.smtp_code = smtp_code
        self.used_fallback = used_fallback
        self.safe_detail = safe_detail or user_safe_message(error_code)
        super().__init__(self.safe_detail)


@runtime_checkable
class EmailProvider(Protocol):
    name: str

    def send(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
        attachments: list | None = None,
        sender_name: str | None = None,
        sender_email: str | None = None,
        reply_to_email: str | None = None,
        reply_to_name: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        html_body: str | None = None,
    ) -> ProviderSendResult: ...

    def health(self, *, live: bool = False) -> dict: ...
