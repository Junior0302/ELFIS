"""Noms d'événements centralisés — convention module.entity.action.vN."""

from __future__ import annotations


class EventNames:
    """Constantes stables pour le bus (pas de chaînes dispersées)."""

    VAULT_DOCUMENT_ARCHIVED = "vault.document.archived.v1"
    VAULT_DOCUMENT_REUSED = "vault.document.reused.v1"

    DELIVERY_EMAIL_STARTED = "delivery.email.started.v1"
    DELIVERY_EMAIL_SENT = "delivery.email.sent.v1"
    DELIVERY_EMAIL_FAILED = "delivery.email.failed.v1"

    # Préparés — pas encore publiés systématiquement
    BILLING_INVOICE_CREATED = "billing.invoice.created.v1"
    BILLING_INVOICE_SENT = "billing.invoice.sent.v1"
    BILLING_QUOTE_SENT = "billing.quote.sent.v1"
    BILLING_CREDIT_NOTE_SENT = "billing.credit_note.sent.v1"


ALL_KNOWN_EVENT_NAMES: frozenset[str] = frozenset(
    getattr(EventNames, name)
    for name in dir(EventNames)
    if name.isupper() and not name.startswith("_")
)
