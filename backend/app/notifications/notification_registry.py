"""Registry léger (templates déjà dans templates/)."""

from __future__ import annotations

from app.notifications.templates import get_template, list_templates

__all__ = ["get_template", "list_templates"]
