"""Pipeline Validation & Mapping — orchestration légère."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.validation_mapping.service import ValidationMappingService


def run_validation_pipeline(
    db: Session,
    *,
    document_id: str,
    organization_id: int,
    actor_user_id: int | None = None,
) -> dict[str, Any]:
    """Démarre la session de validation (pas d'import)."""
    svc = ValidationMappingService(db)
    session = svc.start_or_get(
        document_id, organization_id, actor_user_id=actor_user_id
    )
    return {
        "validation_session_id": session.id,
        "status": session.status,
        "import_executed": False,
        "business_entities_created": False,
    }
