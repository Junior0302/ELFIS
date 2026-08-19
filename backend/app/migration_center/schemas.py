"""Schémas Pydantic — Migration Center."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.migration_center.enums import (
    AccountantStatus,
    CompanyAgeRange,
    JoinReason,
    LegalForm,
    MigrationMode,
    TeamSize,
)
from app.migration_center.progress.schemas import MigrationProgressPayload
from app.migration_center.profile_utils import ensure_profile_envelope, unwrap_company_profile


class CompanyProfilePayload(BaseModel):
    """Profil déclaré par l’utilisateur (contenu métier)."""

    model_config = ConfigDict(extra="forbid")

    company_age_range: CompanyAgeRange
    legal_form: LegalForm
    team_size: TeamSize
    accountant_status: AccountantStatus
    join_reasons: list[JoinReason] = Field(min_length=1)
    other_legal_form: str | None = None
    other_join_reason: str | None = None
    answers_metadata: dict[str, Any] | None = None

    @field_validator("join_reasons")
    @classmethod
    def _dedupe_reasons(cls, value: list[JoinReason]) -> list[JoinReason]:
        seen: set[str] = set()
        out: list[JoinReason] = []
        for r in value:
            if r.value in seen:
                continue
            seen.add(r.value)
            out.append(r)
        if not out:
            raise ValueError("Au moins une raison est requise")
        return out

    @model_validator(mode="after")
    def _require_other_fields(self) -> CompanyProfilePayload:
        if self.legal_form == LegalForm.OTHER:
            if not (self.other_legal_form or "").strip():
                raise ValueError("other_legal_form est obligatoire lorsque legal_form=other")
        if JoinReason.OTHER in self.join_reasons:
            if not (self.other_join_reason or "").strip():
                raise ValueError("other_join_reason est obligatoire lorsque join_reasons contient other")
        return self


# Alias Sprint 1
CompanyProfileIn = CompanyProfilePayload


class MigrationProfilePayload(BaseModel):
    """Informations de fonctionnement de la migration (pas de données IA)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    data: dict[str, Any] = Field(default_factory=dict)


class AIProfilePayload(BaseModel):
    """Détections automatiques futures — vide pour cette passe."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    data: dict[str, Any] = Field(default_factory=dict)


class SourcesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ids: list[str] = Field(min_length=1)
    version: int | None = None


class SessionCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: MigrationMode
    configuration: dict[str, Any] | None = None


class SessionContinueIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int | None = None


class SessionCancelIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=255)
    version: int | None = None


class ProfilePatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: CompanyProfileIn
    version: int | None = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    migration_session_token: str
    organization_id: int
    created_by_user_id: int | None = None
    mode: str
    status: str
    current_step: int
    company_profile: dict[str, Any] | None = None
    migration_profile: dict[str, Any] | None = None
    ai_profile: dict[str, Any] | None = None
    selected_sources: list[str] | None = None
    configuration: dict[str, Any] | None = None
    progress: dict[str, Any] | None = None
    answers_metadata: dict[str, Any] | None = None
    version: int
    started_at: datetime | None = None
    last_activity_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_profiles(cls, data: Any) -> Any:
        if hasattr(data, "company_profile"):
            # ORM object
            return {
                "id": data.id,
                "migration_session_token": getattr(data, "migration_session_token", None) or "",
                "organization_id": data.organization_id,
                "created_by_user_id": data.created_by_user_id,
                "mode": data.mode,
                "status": data.status,
                "current_step": data.current_step,
                "company_profile": unwrap_company_profile(data.company_profile),
                "migration_profile": ensure_profile_envelope(
                    getattr(data, "migration_profile", None)
                ),
                "ai_profile": ensure_profile_envelope(getattr(data, "ai_profile", None)),
                "selected_sources": data.selected_sources,
                "configuration": data.configuration,
                "progress": data.progress,
                "answers_metadata": data.answers_metadata,
                "version": data.version,
                "started_at": data.started_at,
                "last_activity_at": data.last_activity_at,
                "completed_at": data.completed_at,
                "cancelled_at": data.cancelled_at,
                "cancel_reason": data.cancel_reason,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
            }
        if isinstance(data, dict) and "company_profile" in data:
            data = dict(data)
            data["company_profile"] = unwrap_company_profile(data.get("company_profile"))
            data["migration_profile"] = ensure_profile_envelope(data.get("migration_profile"))
            data["ai_profile"] = ensure_profile_envelope(data.get("ai_profile"))
        return data


class SessionDetailOut(SessionOut):
    """Session + timeline + activités récentes (resume / lecture enrichie)."""

    timeline: list[dict[str, Any]] = Field(default_factory=list)
    recent_activities: list[dict[str, Any]] = Field(default_factory=list)


class SessionListOut(BaseModel):
    items: list[SessionOut]
    total: int
    limit: int
    offset: int


class SourceCatalogOut(BaseModel):
    items: list[dict[str, Any]]


class TimelineEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: int
    migration_session_id: str
    step_key: str
    step_order: int
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def _map_metadata(cls, data: Any) -> Any:
        if hasattr(data, "metadata_json"):
            return {
                "id": data.id,
                "organization_id": data.organization_id,
                "migration_session_id": data.migration_session_id,
                "step_key": data.step_key,
                "step_order": data.step_order,
                "status": data.status,
                "started_at": data.started_at,
                "completed_at": data.completed_at,
                "duration_ms": data.duration_ms,
                "metadata": data.metadata_json or {},
                "created_at": data.created_at,
                "updated_at": data.updated_at,
            }
        return data


class TimelineListOut(BaseModel):
    items: list[TimelineEntryOut]


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: int
    migration_session_id: str
    activity_type: str
    title: str
    description: str | None = None
    severity: str
    actor_type: str
    actor_user_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None
    created_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def _map_metadata(cls, data: Any) -> Any:
        if hasattr(data, "metadata_json"):
            return {
                "id": data.id,
                "organization_id": data.organization_id,
                "migration_session_id": data.migration_session_id,
                "activity_type": data.activity_type,
                "title": data.title,
                "description": data.description,
                "severity": data.severity,
                "actor_type": data.actor_type,
                "actor_user_id": data.actor_user_id,
                "metadata": data.metadata_json or {},
                "occurred_at": data.occurred_at,
                "created_at": data.created_at,
            }
        return data


class ActivityListOut(BaseModel):
    items: list[ActivityOut]


class ProgressOut(BaseModel):
    progress: MigrationProgressPayload
