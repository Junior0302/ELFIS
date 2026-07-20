"""Templates billing / email documentaire."""

from app.notifications.templates.base_templates import (
    DocumentEmailFailedTemplate,
    DocumentEmailSentTemplate,
)

__all__ = ["DocumentEmailFailedTemplate", "DocumentEmailSentTemplate"]
