"""Schémas API Workspace Provisioning V1."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.workspace_provisioning.steps import (
    ALLOWED_INDUSTRIES,
    ALLOWED_VAT_STATUSES,
    COMPANY_NAME_MAX,
    COMPANY_NAME_MIN,
    INDUSTRY_OTHER_MAX,
    INDUSTRY_OTHER_MIN,
    VAT_NUMBER_MAX,
)

VatStatus = Literal["vat_registered", "vat_not_registered", "vat_unknown"]
ProvisionStatus = Literal["pending", "running", "completed", "failed"]


class WorkspaceProvisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    company_name: str = Field(min_length=1, max_length=COMPANY_NAME_MAX)
    industry: str
    industry_other: str | None = None
    country: str
    currency: str
    vat_status: str
    vat_number: str | None = None

    @field_validator("company_name")
    @classmethod
    def _company_name(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if len(cleaned) < COMPANY_NAME_MIN:
            raise ValueError("Le nom doit contenir au moins 2 caractères.")
        if len(cleaned) > COMPANY_NAME_MAX:
            raise ValueError("Le nom ne peut pas dépasser 120 caractères.")
        return cleaned

    @field_validator("industry")
    @classmethod
    def _industry(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if cleaned not in ALLOWED_INDUSTRIES:
            raise ValueError("Secteur d’activité invalide.")
        return cleaned

    @field_validator("country")
    @classmethod
    def _country(cls, value: str) -> str:
        cleaned = (value or "").strip().upper()
        if len(cleaned) != 2 or not cleaned.isalpha():
            raise ValueError("Code pays ISO alpha-2 invalide.")
        return cleaned

    @field_validator("currency")
    @classmethod
    def _currency(cls, value: str) -> str:
        cleaned = (value or "").strip().upper()
        if len(cleaned) != 3 or not cleaned.isalpha():
            raise ValueError("Code devise ISO 4217 invalide.")
        return cleaned

    @field_validator("vat_status")
    @classmethod
    def _vat_status(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if cleaned not in ALLOWED_VAT_STATUSES:
            raise ValueError("Statut TVA invalide.")
        return cleaned

    @field_validator("vat_number")
    @classmethod
    def _vat_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = "".join(str(value).split()).upper()
        if not cleaned:
            return None
        if len(cleaned) > VAT_NUMBER_MAX or not cleaned.isalnum():
            raise ValueError("Numéro de TVA invalide.")
        return cleaned

    @model_validator(mode="after")
    def _industry_other_required(self) -> WorkspaceProvisionRequest:
        if self.industry == "other":
            other = (self.industry_other or "").strip()
            if len(other) < INDUSTRY_OTHER_MIN:
                raise ValueError("Précisez votre secteur d’activité.")
            if len(other) > INDUSTRY_OTHER_MAX:
                raise ValueError("Le secteur ne peut pas dépasser 100 caractères.")
            self.industry_other = other
        else:
            self.industry_other = None
        if self.vat_status != "vat_registered":
            self.vat_number = None
        return self


class WorkspaceProvisionStatusOut(BaseModel):
    status: ProvisionStatus
    current_step: str
    progress: int
    setup_completed: bool
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    provisioning_version: int = 1

    @classmethod
    def from_run(
        cls,
        *,
        status: str,
        current_step: str,
        progress: int,
        setup_completed: bool,
        error_code: str = "",
        error_message_safe: str = "",
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        provisioning_version: int = 1,
    ) -> WorkspaceProvisionStatusOut:
        return cls(
            status=status,  # type: ignore[arg-type]
            current_step=current_step,
            progress=progress,
            setup_completed=setup_completed,
            error_code=error_code or None,
            error_message=error_message_safe or None,
            started_at=started_at,
            completed_at=completed_at,
            provisioning_version=provisioning_version,
        )


def validation_error_payload(exc: Any) -> dict[str, Any]:
    return {
        "code": "INVALID_SETUP_DRAFT",
        "message": "Les informations de configuration sont invalides.",
        "details": getattr(exc, "errors", lambda: [])(),
    }
