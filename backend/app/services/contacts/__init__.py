"""Contacts intelligents (clients / fournisseurs) depuis les documents."""

from app.services.contacts.detection_service import (
    generate_suggestions,
    list_pending_suggestions,
    safe_generate_suggestions,
)

__all__ = [
    "generate_suggestions",
    "list_pending_suggestions",
    "safe_generate_suggestions",
]
