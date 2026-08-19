"""Service métier — Validation & Mapping Center V1 (aucun import)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.document_extraction.enums import ExtractionStatus
from app.document_extraction.repository import DocumentExtractionRepository
from app.document_intake.enums import DocumentLifecycleStatus, LifecycleActorType
from app.document_intake.lifecycle_service import DocumentLifecycleService
from app.document_intake.repository import DocumentIntakeRepository
from app.validation_mapping.duplicates import detect_document_duplicates
from app.validation_mapping.enums import (
    FieldValidationStatus,
    MatchResolution,
    ValidationSessionStatus,
)
from app.validation_mapping.events import publish_validation_event
from app.validation_mapping.exceptions import (
    ValidationConflictError,
    ValidationNotFoundError,
    ValidationStateError,
)
from app.validation_mapping.field_editor import flatten_fields, set_path
from app.validation_mapping.history import append_history, list_history
from app.validation_mapping.matcher import match_party
from app.validation_mapping.models import (
    ElfisValidationDuplicate,
    ElfisValidationField,
    ElfisValidationMatch,
    ElfisValidationSession,
)
from app.validation_mapping.repository import ValidationMappingRepository
from app.validation_mapping.validators import validate_document_data

logger = logging.getLogger(__name__)


class ValidationMappingService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = ValidationMappingRepository(db)
        self._intake = DocumentIntakeRepository(db)
        self._extr = DocumentExtractionRepository(db)
        self._lifecycle = DocumentLifecycleService(db)

    def get_session(
        self, session_id: str, organization_id: int
    ) -> ElfisValidationSession:
        row = self._repo.get_session_for_org(session_id, organization_id)
        if not row:
            raise ValidationNotFoundError("not_found", "Session de validation introuvable")
        return row

    def get_for_document(
        self, document_id: str, organization_id: int
    ) -> ElfisValidationSession:
        item = self._intake.get_for_org(document_id, organization_id)
        if not item:
            raise ValidationNotFoundError("not_found", "Document introuvable")
        row = self._repo.find_for_item(
            organization_id=organization_id, document_intake_item_id=document_id
        )
        if not row:
            raise ValidationNotFoundError("not_found", "Validation introuvable")
        return row

    def list_for_migration(
        self, *, organization_id: int, migration_session_id: str
    ) -> list[ElfisValidationSession]:
        return self._repo.list_for_migration(
            organization_id=organization_id, migration_session_id=migration_session_id
        )

    def start_or_get(
        self,
        document_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
    ) -> ElfisValidationSession:
        item = self._intake.get_for_org(document_id, organization_id)
        if not item:
            raise ValidationNotFoundError("not_found", "Document introuvable")

        st = item.lifecycle_status or item.status
        if st in (
            DocumentLifecycleStatus.QUARANTINED.value,
            DocumentLifecycleStatus.CANCELLED.value,
        ):
            raise ValidationStateError("not_eligible", "Document non éligible")

        extractions = self._extr.list_for_item(
            organization_id=organization_id, document_intake_item_id=item.id
        )
        extraction = next(
            (
                e
                for e in extractions
                if e.status
                in (
                    ExtractionStatus.AWAITING_HUMAN_VALIDATION.value,
                    ExtractionStatus.COMPLETED.value,
                    ExtractionStatus.COMPLETED_WITH_WARNINGS.value,
                )
            ),
            extractions[0] if extractions else None,
        )
        if not extraction:
            raise ValidationStateError("extraction_missing", "Extraction absente")

        existing = self._repo.find_for_extraction(
            organization_id=organization_id, extraction_id=extraction.id
        )
        if existing and existing.status != ValidationSessionStatus.REJECTED.value:
            return existing

        data = dict(extraction.structured_data or {})
        provenance = dict(extraction.field_provenance or {})
        flat = flatten_fields(data)
        now = datetime.utcnow()
        session = ElfisValidationSession(
            id=str(uuid4()),
            organization_id=organization_id,
            migration_session_id=item.migration_session_id,
            document_intake_item_id=item.id,
            universal_document_id=item.universal_document_id,
            extraction_id=extraction.id,
            status=ValidationSessionStatus.VALIDATING.value,
            validated_data=data,
            field_states={},
            warnings_json=list(extraction.warnings_json or []),
            errors_json=list(extraction.errors_json or []),
            duplicate_summary={},
            matching_summary={},
            progress_percent=10,
            started_at=now,
            created_by_user_id=actor_user_id,
            created_at=now,
            updated_at=now,
            version=1,
        )
        self._repo.add_session(session, commit=False)

        field_states: dict[str, str] = {}
        for path, value in flat.items():
            prov = provenance.get(path) if isinstance(provenance.get(path), dict) else {}
            conf = float(prov.get("confidence") or extraction.overall_confidence or 0.5)
            status = (
                FieldValidationStatus.UNKNOWN.value
                if conf < 0.70
                else FieldValidationStatus.UNKNOWN.value
            )
            # Jamais auto-accept basse confiance
            field_states[path] = status
            self._repo.add_field(
                ElfisValidationField(
                    id=str(uuid4()),
                    organization_id=organization_id,
                    validation_session_id=session.id,
                    field_path=path,
                    ai_value=value,
                    current_value=value,
                    status=status,
                    confidence=conf,
                    provenance={
                        "source": prov.get("source"),
                        "extractor_name": prov.get("extractor_name"),
                        "extractor_version": prov.get("extractor_version"),
                        "page_number": prov.get("page_number"),
                        "bounding_box": prov.get("bounding_box"),
                        "confidence": conf,
                    },
                    warnings_json=list(prov.get("warnings") or []),
                ),
                commit=False,
            )
        session.field_states = field_states

        actor_kw = {
            "organization_id": organization_id,
            "actor_type": LifecycleActorType.USER.value
            if actor_user_id
            else LifecycleActorType.SYSTEM.value,
            "actor_user_id": actor_user_id,
            "commit": False,
        }
        if st == DocumentLifecycleStatus.AWAITING_VALIDATION.value:
            self._lifecycle.mark_human_validating(
                item, reason_code="validation_started", **actor_kw
            )

        # Doublons + matching (propositions)
        dups = detect_document_duplicates(
            self._db,
            organization_id=organization_id,
            current_extraction=extraction,
            validated_data=data,
        )
        for d in dups:
            self._repo.add_duplicate(
                ElfisValidationDuplicate(
                    id=str(uuid4()),
                    organization_id=organization_id,
                    validation_session_id=session.id,
                    other_document_id=d.get("other_document_id"),
                    other_universal_document_id=d.get("other_universal_document_id"),
                    severity=d["severity"],
                    score=d["score"],
                    matched_fields=d["matched_fields"],
                    explanation=d.get("explanation"),
                ),
                commit=False,
            )
        session.duplicate_summary = {"count": len(dups), "top": dups[:3]}

        matches_all: list[dict[str, Any]] = []
        for role, key in (("supplier", "supplier"), ("customer", "customer"), ("merchant", None)):
            party = data.get(key) if key else None
            if role == "merchant" and data.get("merchant_name"):
                party = {
                    "name": data.get("merchant_name"),
                    "address": data.get("merchant_address"),
                }
            if not isinstance(party, dict):
                continue
            for m in match_party(
                self._db, organization_id=organization_id, party=party, party_role=role
            ):
                matches_all.append(m)
                self._repo.add_match(
                    ElfisValidationMatch(
                        id=str(uuid4()),
                        organization_id=organization_id,
                        validation_session_id=session.id,
                        party_role=m["party_role"],
                        category=m["category"],
                        score=m["score"],
                        contact_id=m.get("contact_id"),
                        contact_label=m.get("contact_label"),
                        matched_criteria=m.get("matched_criteria") or [],
                        explanation=m.get("explanation"),
                        resolution=MatchResolution.UNRESOLVED.value,
                    ),
                    commit=False,
                )
        session.matching_summary = {"count": len(matches_all)}

        checks = validate_document_data(data)
        session.errors_json = list(session.errors_json or []) + list(checks.get("errors") or [])
        session.warnings_json = list(session.warnings_json or []) + list(
            checks.get("warnings") or []
        )
        session.progress_percent = 40
        self._repo.save_session(session, commit=False)

        publish_validation_event(
            self._db,
            event_type="validation.started",
            session=session,
            actor_user_id=actor_user_id,
            metadata={"progress_percent": 40},
            commit=False,
        )
        if dups:
            publish_validation_event(
                self._db,
                event_type="duplicate.detected",
                session=session,
                actor_user_id=actor_user_id,
                metadata={"duplicate_count": len(dups)},
                commit=False,
            )
        publish_validation_event(
            self._db,
            event_type="matching.completed",
            session=session,
            actor_user_id=actor_user_id,
            metadata={"match_count": len(matches_all)},
            commit=False,
        )
        self._db.commit()
        self._db.refresh(session)
        return session

    def list_fields(
        self, session_id: str, organization_id: int
    ) -> list[ElfisValidationField]:
        self.get_session(session_id, organization_id)
        return self._repo.list_fields(session_id)

    def edit_field(
        self,
        session_id: str,
        organization_id: int,
        *,
        field_path: str,
        new_value: Any,
        actor_user_id: int | None,
        reason: str | None = None,
        action: str = "edit",
    ) -> ElfisValidationField:
        session = self.get_session(session_id, organization_id)
        if session.status not in (
            ValidationSessionStatus.VALIDATING.value,
            ValidationSessionStatus.PENDING.value,
        ):
            raise ValidationStateError("not_editable", "Session non éditable")

        field = self._repo.get_field(session_id, field_path)
        if not field:
            raise ValidationNotFoundError("field_not_found", "Champ introuvable")

        old = field.current_value
        if action == "accept":
            field.status = FieldValidationStatus.ACCEPTED.value
            field.current_value = field.ai_value if field.current_value is None else field.current_value
            evt = "field.accepted"
            hist_action = "accept"
        elif action == "reject":
            field.status = FieldValidationStatus.REJECTED.value
            evt = "field.edited"
            hist_action = "reject"
        else:
            field.current_value = new_value
            field.status = FieldValidationStatus.EDITED.value
            session.validated_data = set_path(
                dict(session.validated_data or {}), field_path, new_value
            )
            evt = "field.edited"
            hist_action = "edit"

        states = dict(session.field_states or {})
        states[field_path] = field.status
        session.field_states = states
        session.version = int(session.version or 1) + 1
        session.progress_percent = min(90, max(40, session.progress_percent or 40) + 2)

        append_history(
            self._db,
            organization_id=organization_id,
            validation_session_id=session.id,
            field_path=field_path,
            old_value=old,
            new_value=field.current_value,
            action=hist_action,
            actor_user_id=actor_user_id,
            reason=reason,
            commit=False,
        )
        # Provenance user_corrected uniquement après édition humaine
        if hist_action == "edit":
            prov = dict(field.provenance or {})
            prov["source"] = "user_corrected"
            field.provenance = prov

        self._repo.save_session(session, commit=False)
        publish_validation_event(
            self._db,
            event_type=evt,
            session=session,
            actor_user_id=actor_user_id,
            metadata={"field_path": field_path, "action": hist_action},
            commit=False,
        )
        self._db.commit()
        self._db.refresh(field)
        return field

    def validate_document(
        self,
        session_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        mark_ready: bool = True,
    ) -> ElfisValidationSession:
        session = self.get_session(session_id, organization_id)
        if session.status in (
            ValidationSessionStatus.REJECTED.value,
            ValidationSessionStatus.CANCELLED.value,
        ):
            raise ValidationStateError("terminal", "Session terminale")

        checks = validate_document_data(session.validated_data or {})
        if checks.get("errors"):
            session.errors_json = list(checks["errors"])
            session.warnings_json = list(
                set(list(session.warnings_json or []) + list(checks.get("warnings") or []))
            )
            self._repo.save_session(session, commit=True)
            raise ValidationConflictError(
                "validation_errors",
                f"Erreurs bloquantes: {', '.join(checks['errors'][:5])}",
            )

        # Champs critiques basse confiance non acceptés/édités → bloquer auto
        fields = self._repo.list_fields(session_id)
        critical_prefixes = (
            "document_number",
            "document_date",
            "supplier.name",
            "amounts.total_including_tax",
            "currency",
        )
        for f in fields:
            if any(f.field_path.startswith(p) for p in critical_prefixes):
                if (f.confidence or 0) < 0.40 and f.status == FieldValidationStatus.UNKNOWN.value:
                    raise ValidationConflictError(
                        "low_confidence_unreviewed",
                        f"Champ critique non revu: {f.field_path}",
                    )

        item = self._intake.get_for_org(session.document_intake_item_id, organization_id)
        actor_kw = {
            "organization_id": organization_id,
            "actor_type": LifecycleActorType.USER.value
            if actor_user_id
            else LifecycleActorType.SYSTEM.value,
            "actor_user_id": actor_user_id,
            "commit": False,
        }
        if item and (item.lifecycle_status or item.status) == DocumentLifecycleStatus.HUMAN_VALIDATING.value:
            self._lifecycle.mark_validated_by_user(
                item, reason_code="human_validated", **actor_kw
            )
        session.status = ValidationSessionStatus.VALIDATED.value
        session.validated_by_user_id = actor_user_id
        session.progress_percent = 85
        session.completed_at = datetime.utcnow()
        session.version = int(session.version or 1) + 1
        self._repo.save_session(session, commit=False)
        publish_validation_event(
            self._db,
            event_type="document.validated",
            session=session,
            actor_user_id=actor_user_id,
            commit=False,
        )

        if mark_ready and item:
            if (item.lifecycle_status or item.status) == DocumentLifecycleStatus.VALIDATED_BY_USER.value:
                self._lifecycle.mark_ready_for_import(
                    item, reason_code="ready_no_import", **actor_kw
                )
            session.status = ValidationSessionStatus.READY_FOR_IMPORT.value
            session.progress_percent = 100
            self._repo.save_session(session, commit=False)
            publish_validation_event(
                self._db,
                event_type="ready_for_import",
                session=session,
                actor_user_id=actor_user_id,
                commit=False,
            )

        self._db.commit()
        self._db.refresh(session)
        return session

    def reject_document(
        self,
        session_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        reason: str | None = None,
    ) -> ElfisValidationSession:
        session = self.get_session(session_id, organization_id)
        item = self._intake.get_for_org(session.document_intake_item_id, organization_id)
        actor_kw = {
            "organization_id": organization_id,
            "actor_type": LifecycleActorType.USER.value
            if actor_user_id
            else LifecycleActorType.SYSTEM.value,
            "actor_user_id": actor_user_id,
            "commit": False,
        }
        if item and (item.lifecycle_status or item.status) in (
            DocumentLifecycleStatus.AWAITING_VALIDATION.value,
            DocumentLifecycleStatus.HUMAN_VALIDATING.value,
            DocumentLifecycleStatus.VALIDATED_BY_USER.value,
        ):
            self._lifecycle.mark_rejected(
                item, reason_code="validation_rejected", **actor_kw
            )
        session.status = ValidationSessionStatus.REJECTED.value
        session.rejection_reason = (reason or "")[:500]
        session.completed_at = datetime.utcnow()
        session.progress_percent = 100
        session.version = int(session.version or 1) + 1
        append_history(
            self._db,
            organization_id=organization_id,
            validation_session_id=session.id,
            field_path="__document__",
            old_value=None,
            new_value="rejected",
            action="reject",
            actor_user_id=actor_user_id,
            reason=reason,
            commit=False,
        )
        self._repo.save_session(session, commit=False)
        publish_validation_event(
            self._db,
            event_type="document.rejected",
            session=session,
            actor_user_id=actor_user_id,
            commit=False,
        )
        self._db.commit()
        self._db.refresh(session)
        return session

    def get_history(self, session_id: str, organization_id: int):
        self.get_session(session_id, organization_id)
        return list_history(
            self._db, organization_id=organization_id, validation_session_id=session_id
        )

    def get_duplicates(self, session_id: str, organization_id: int):
        self.get_session(session_id, organization_id)
        return self._repo.list_duplicates(session_id)

    def get_matches(self, session_id: str, organization_id: int):
        self.get_session(session_id, organization_id)
        return self._repo.list_matches(session_id)

    def resolve_match(
        self,
        match_id: str,
        organization_id: int,
        *,
        resolution: str,
        actor_user_id: int | None = None,
    ) -> ElfisValidationMatch:
        row = self._repo.get_match(match_id, organization_id)
        if not row:
            raise ValidationNotFoundError("not_found", "Match introuvable")
        if resolution not in {r.value for r in MatchResolution}:
            raise ValidationConflictError("invalid_resolution", "Résolution invalide")
        # Jamais de création de contact
        if resolution == MatchResolution.USE_EXISTING.value and not row.contact_id:
            raise ValidationConflictError(
                "no_contact", "Aucune fiche existante à associer"
            )
        row.resolution = resolution
        row.updated_at = datetime.utcnow()
        session = self.get_session(row.validation_session_id, organization_id)
        append_history(
            self._db,
            organization_id=organization_id,
            validation_session_id=session.id,
            field_path=f"match.{row.party_role}",
            old_value=MatchResolution.UNRESOLVED.value,
            new_value=resolution,
            action="resolve_match",
            actor_user_id=actor_user_id,
            reason=None,
            commit=False,
        )
        self._db.commit()
        self._db.refresh(row)
        return row

    def start_session_batch(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        actor_user_id: int | None = None,
    ) -> dict[str, Any]:
        items, _ = self._intake.list_items(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            limit=100,
            offset=0,
        )
        results: list[ElfisValidationSession] = []
        errors: list[dict[str, str]] = []
        for item in items:
            st = item.lifecycle_status or item.status
            if st not in (
                DocumentLifecycleStatus.AWAITING_VALIDATION.value,
                DocumentLifecycleStatus.HUMAN_VALIDATING.value,
                DocumentLifecycleStatus.VALIDATED_BY_USER.value,
                DocumentLifecycleStatus.READY_FOR_IMPORT.value,
            ):
                continue
            try:
                results.append(
                    self.start_or_get(
                        item.id, organization_id, actor_user_id=actor_user_id
                    )
                )
            except Exception as exc:
                errors.append(
                    {
                        "item_id": item.id,
                        "code": getattr(exc, "code", type(exc).__name__),
                        "message": str(getattr(exc, "message", exc))[:200],
                    }
                )
        return {"started": len(results), "errors": errors, "items": results}
