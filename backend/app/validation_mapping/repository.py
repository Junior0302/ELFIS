"""Repository Validation & Mapping."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.validation_mapping.models import (
    ElfisValidationDuplicate,
    ElfisValidationField,
    ElfisValidationMatch,
    ElfisValidationSession,
)


class ValidationMappingRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_session(self, session_id: str) -> ElfisValidationSession | None:
        return self._db.get(ElfisValidationSession, session_id)

    def get_session_for_org(
        self, session_id: str, organization_id: int
    ) -> ElfisValidationSession | None:
        row = self.get_session(session_id)
        if not row or row.organization_id != organization_id:
            return None
        return row

    def find_for_extraction(
        self, *, organization_id: int, extraction_id: str
    ) -> ElfisValidationSession | None:
        return (
            self._db.query(ElfisValidationSession)
            .filter(ElfisValidationSession.organization_id == organization_id)
            .filter(ElfisValidationSession.extraction_id == extraction_id)
            .order_by(ElfisValidationSession.created_at.desc())
            .first()
        )

    def find_for_item(
        self, *, organization_id: int, document_intake_item_id: str
    ) -> ElfisValidationSession | None:
        return (
            self._db.query(ElfisValidationSession)
            .filter(ElfisValidationSession.organization_id == organization_id)
            .filter(ElfisValidationSession.document_intake_item_id == document_intake_item_id)
            .order_by(ElfisValidationSession.created_at.desc())
            .first()
        )

    def list_for_migration(
        self, *, organization_id: int, migration_session_id: str, limit: int = 100
    ) -> list[ElfisValidationSession]:
        return (
            self._db.query(ElfisValidationSession)
            .filter(ElfisValidationSession.organization_id == organization_id)
            .filter(ElfisValidationSession.migration_session_id == migration_session_id)
            .order_by(ElfisValidationSession.updated_at.desc())
            .limit(max(1, min(limit, 500)))
            .all()
        )

    def add_session(
        self, row: ElfisValidationSession, *, commit: bool = True
    ) -> ElfisValidationSession:
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def save_session(
        self, row: ElfisValidationSession, *, commit: bool = True
    ) -> ElfisValidationSession:
        row.updated_at = datetime.utcnow()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def list_fields(
        self, validation_session_id: str
    ) -> list[ElfisValidationField]:
        return (
            self._db.query(ElfisValidationField)
            .filter(ElfisValidationField.validation_session_id == validation_session_id)
            .order_by(ElfisValidationField.field_path.asc())
            .all()
        )

    def get_field(
        self, validation_session_id: str, field_path: str
    ) -> ElfisValidationField | None:
        return (
            self._db.query(ElfisValidationField)
            .filter(ElfisValidationField.validation_session_id == validation_session_id)
            .filter(ElfisValidationField.field_path == field_path)
            .first()
        )

    def add_field(self, row: ElfisValidationField, *, commit: bool = False) -> ElfisValidationField:
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def clear_duplicates(self, validation_session_id: str) -> None:
        self._db.query(ElfisValidationDuplicate).filter(
            ElfisValidationDuplicate.validation_session_id == validation_session_id
        ).delete()

    def add_duplicate(self, row: ElfisValidationDuplicate, *, commit: bool = False) -> None:
        self._db.add(row)
        if commit:
            self._db.commit()
        else:
            self._db.flush()

    def list_duplicates(
        self, validation_session_id: str
    ) -> list[ElfisValidationDuplicate]:
        return (
            self._db.query(ElfisValidationDuplicate)
            .filter(ElfisValidationDuplicate.validation_session_id == validation_session_id)
            .order_by(ElfisValidationDuplicate.score.desc())
            .all()
        )

    def clear_matches(self, validation_session_id: str) -> None:
        self._db.query(ElfisValidationMatch).filter(
            ElfisValidationMatch.validation_session_id == validation_session_id
        ).delete()

    def add_match(self, row: ElfisValidationMatch, *, commit: bool = False) -> None:
        self._db.add(row)
        if commit:
            self._db.commit()
        else:
            self._db.flush()

    def list_matches(self, validation_session_id: str) -> list[ElfisValidationMatch]:
        return (
            self._db.query(ElfisValidationMatch)
            .filter(ElfisValidationMatch.validation_session_id == validation_session_id)
            .order_by(ElfisValidationMatch.score.desc())
            .all()
        )

    def get_match(
        self, match_id: str, organization_id: int
    ) -> ElfisValidationMatch | None:
        row = self._db.get(ElfisValidationMatch, match_id)
        if not row or row.organization_id != organization_id:
            return None
        return row
