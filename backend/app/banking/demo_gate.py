"""Gate explicite du connecteur Banque Démo ELFIS."""

from __future__ import annotations

from app.config import settings
from app.security.security_config import is_production

DEMO_PROVIDER = "demo"
FICTIONAL_BANK_LABEL = "Banque Démo ELFIS — données fictives"


def is_demo_bank_enabled() -> bool:
    """Production : off sauf ELFIS_DEMO_BANK_ENABLED=true. Hors prod : on par défaut."""
    raw = getattr(settings, "elfis_demo_bank_enabled", None)
    if raw is True:
        return True
    if raw is False:
        return False
    return not is_production()
