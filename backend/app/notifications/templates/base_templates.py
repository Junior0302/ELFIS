"""Registry de templates de notification."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.notifications.notification_schemas import RenderedNotification
from app.notifications.notification_types import (
    NotificationCategories,
    NotificationChannel,
    NotificationSeverity,
    NotificationTypes,
    TEMPLATE_DOCUMENT_ARCHIVED,
    TEMPLATE_DOCUMENT_EMAIL_FAILED,
    TEMPLATE_DOCUMENT_EMAIL_SENT,
    TEMPLATE_SYSTEM_GENERIC,
)


class NotificationTemplate(ABC):
    template_name: str
    notification_type: str
    category: str
    default_severity: str = NotificationSeverity.INFO
    default_channels: list[str] = [NotificationChannel.IN_APP]
    default_email_enabled: bool = False

    @abstractmethod
    def render(self, data: dict[str, Any]) -> RenderedNotification:
        raise NotImplementedError


class DocumentEmailSentTemplate(NotificationTemplate):
    template_name = TEMPLATE_DOCUMENT_EMAIL_SENT
    notification_type = NotificationTypes.DELIVERY_EMAIL_SENT
    category = NotificationCategories.EMAIL
    default_severity = NotificationSeverity.SUCCESS
    default_channels = [NotificationChannel.IN_APP]
    default_email_enabled = False

    def render(self, data: dict[str, Any]) -> RenderedNotification:
        doc_type = str(data.get("business_document_type") or data.get("document_type") or "document")
        number = str(data.get("document_number") or data.get("business_document_id") or "").strip()
        label = {
            "invoice": "Facture",
            "quote": "Devis",
            "credit_note": "Avoir",
            "customer_invoice": "Facture",
        }.get(doc_type, "Document")
        title = f"{label} envoyé{'e' if label != 'Devis' else ''}"
        if label == "Devis":
            title = "Devis envoyé"
        elif label == "Avoir":
            title = "Avoir envoyé"
        else:
            title = "Facture envoyée"
        body_num = number or "votre document"
        message = f"La {label.lower()} {body_num} a été envoyée avec succès."
        if label == "Devis":
            message = f"Le devis {body_num} a été envoyé avec succès."
        elif label == "Avoir":
            message = f"L’avoir {body_num} a été envoyé avec succès."
        return RenderedNotification(
            title=title,
            message=message,
            action_url="/documents",
            action_label="Consulter le document",
            severity=self.default_severity,
        )


class DocumentEmailFailedTemplate(NotificationTemplate):
    template_name = TEMPLATE_DOCUMENT_EMAIL_FAILED
    notification_type = NotificationTypes.DELIVERY_EMAIL_FAILED
    category = NotificationCategories.EMAIL
    default_severity = NotificationSeverity.ERROR
    default_channels = [NotificationChannel.IN_APP]
    default_email_enabled = False

    def render(self, data: dict[str, Any]) -> RenderedNotification:
        number = str(data.get("document_number") or data.get("business_document_id") or "").strip()
        ref = f" ({number})" if number else ""
        return RenderedNotification(
            title="Échec de l’envoi",
            message=(
                f"Le document{ref} a été archivé, mais l’e-mail n’a pas pu être envoyé. "
                "Vous pourrez réessayer sans recréer la facture."
            ),
            action_url="/facturation",
            action_label="Réessayer l’envoi",
            severity=self.default_severity,
        )


class DocumentArchivedTemplate(NotificationTemplate):
    template_name = TEMPLATE_DOCUMENT_ARCHIVED
    notification_type = NotificationTypes.VAULT_DOCUMENT_ARCHIVED
    category = NotificationCategories.VAULT
    default_severity = NotificationSeverity.INFO
    default_channels = [NotificationChannel.IN_APP]
    default_email_enabled = False

    def render(self, data: dict[str, Any]) -> RenderedNotification:
        number = str(data.get("document_number") or "").strip()
        ref = f" {number}" if number else ""
        return RenderedNotification(
            title="Document archivé",
            message=f"Le document{ref} a été archivé dans ELFIS Vault.",
            action_url="/documents",
            action_label="Voir dans Vault",
            severity=self.default_severity,
        )


class SystemGenericTemplate(NotificationTemplate):
    template_name = TEMPLATE_SYSTEM_GENERIC
    notification_type = NotificationTypes.SYSTEM_WELCOME
    category = NotificationCategories.SYSTEM
    default_severity = NotificationSeverity.INFO
    default_channels = [NotificationChannel.IN_APP, NotificationChannel.EMAIL]
    default_email_enabled = True

    def render(self, data: dict[str, Any]) -> RenderedNotification:
        title = str(data.get("title") or "Notification système")[:200]
        message = str(data.get("message") or "Une notification système est disponible.")[:2000]
        return RenderedNotification(
            title=title,
            message=message,
            email_subject=title,
            email_text=message,
            email_html=f"<p>{message}</p>",
            severity=str(data.get("severity") or self.default_severity),
        )


_TEMPLATES: dict[str, NotificationTemplate] = {
    t.template_name: t
    for t in (
        DocumentEmailSentTemplate(),
        DocumentEmailFailedTemplate(),
        DocumentArchivedTemplate(),
        SystemGenericTemplate(),
    )
}


def get_template(name: str) -> NotificationTemplate:
    template = _TEMPLATES.get(name)
    if not template:
        raise KeyError(f"Template inconnu: {name}")
    return template


def list_templates() -> list[str]:
    return sorted(_TEMPLATES.keys())
