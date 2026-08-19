"""Étapes et progression du provisioning workspace (C1.11)."""

from __future__ import annotations

from typing import Final

PROVISIONING_VERSION: Final[int] = 1

STEP_VALIDATING = "validating_setup"
STEP_SAVING_PROFILE = "saving_company_profile"
STEP_CONFIGURING = "configuring_workspace"
STEP_COMPLETING = "completing_setup"
STEP_COMPLETED = "completed"

PROGRESS_BY_STEP: Final[dict[str, int]] = {
    STEP_VALIDATING: 10,
    STEP_SAVING_PROFILE: 35,
    STEP_CONFIGURING: 65,
    STEP_COMPLETING: 90,
    STEP_COMPLETED: 100,
}

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

ALLOWED_INDUSTRIES: Final[frozenset[str]] = frozenset(
    {
        "commerce",
        "services",
        "construction",
        "transport_logistics",
        "food_hospitality",
        "automotive",
        "health_wellness",
        "real_estate",
        "technology",
        "consulting_training",
        "crafts",
        "other",
    }
)

ALLOWED_VAT_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "vat_registered",
        "vat_not_registered",
        "vat_unknown",
    }
)

COMPANY_NAME_MIN = 2
COMPANY_NAME_MAX = 120
INDUSTRY_OTHER_MIN = 2
INDUSTRY_OTHER_MAX = 100
VAT_NUMBER_MAX = 32

# UI steps (frontend labels map)
UI_STEPS: Final[tuple[tuple[str, str], ...]] = (
    (STEP_VALIDATING, "Vérification de vos informations"),
    (STEP_SAVING_PROFILE, "Enregistrement de votre entreprise"),
    (STEP_CONFIGURING, "Configuration de votre espace"),
    (STEP_COMPLETING, "Finalisation"),
)
