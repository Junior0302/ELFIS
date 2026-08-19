"""Service Import Engine."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.document_intake.enums import DocumentLifecycleStatus
from app.document_intake.lifecycle_service import DocumentLifecycleService
from app.import_engine.audit import write_import_audit
from app.import_engine.enums import ImportRunStatus, RollbackReason
from app.import_engine.events import publish_import_event
from app.import_engine.exceptions import (
    ImportConflictError,
    ImportIdempotencyError,
    ImportNotFoundError,
    ImportStateError,
    ImportValidationError,
)
from app.import_engine.idempotency import (
    build_fingerprint,
    build_idempotency_key,
    get_completed_run_by_fingerprint,
)
from app.import_engine.models import ElfisImportRun
from app.import_engine.pipeline import ImportPipeline
from app.import_engine.repository import ImportRepository
from app.import_engine.rollback import RollbackService
from app.import_engine.schemas import ReadyDocumentOut
from app.import_engine.validators import assert_document_importable
from app.validation_mapping.enums import ValidationSessionStatus
from app.validation_mapping.models import ElfisValidationSession


class ImportEngineService:
    def __init__(self, db: Session):
        self._db = db
        self._repo = ImportRepository(db)
        self._pipeline = ImportPipeline(db)
        self._lifecycle = DocumentLifecycleService(db)

    def list_ready_documents(
        self,
        *,
        organization_id: int,
        migration_session_id: str | None = None,
    ) -> list[ReadyDocumentOut]:
        q = (
            self._db.query(ElfisValidationSession)
            .filter(ElfisValidationSession.organization_id == organization_id)
            .filter(
                ElfisValidationSession.status
                == ValidationSessionStatus.READY_FOR_IMPORT.value
            )
        )
        if migration_session_id:
            q = q.filter(
                ElfisValidationSession.migration_session_id == migration_session_id
            )
        sessions = q.order_by(ElfisValidationSession.updated_at.desc()).all()
        out: list[ReadyDocumentOut] = []
        for s in sessions:
            fp = build_fingerprint(
                organization_id=organization_id,
                document_intake_item_id=s.document_intake_item_id,
                validation_session_id=s.id,
                validation_version=int(s.version or 1),
            )
            existing = get_completed_run_by_fingerprint(
                self._db, organization_id=organization_id, fingerprint=fp
            )
            already = bool(
                existing and existing.status == ImportRunStatus.COMPLETED.value
            )
            out.append(
                ReadyDocumentOut(
                    document_id=s.document_intake_item_id,
                    universal_document_id=s.universal_document_id,
                    validation_session_id=s.id,
                    validation_version=int(s.version or 1),
                    schema_name=None,
                    status=s.status,
                    already_imported=already,
                )
            )
        return out

    def import_document(
        self,
        *,
        organization_id: int,
        document_id: str,
        actor_user_id: int | None,
    ) -> ElfisImportRun:
        from app.import_engine.validators import get_intake_item, get_ready_validation_session

        # Idempotence avant contrôles d'état (document déjà import_completed)
        try:
            item = get_intake_item(
                self._db, organization_id=organization_id, document_id=document_id
            )
            session = get_ready_validation_session(
                self._db, organization_id=organization_id, document_id=document_id
            )
            fp = build_fingerprint(
                organization_id=organization_id,
                document_intake_item_id=document_id,
                validation_session_id=session.id,
                validation_version=int(session.version or 1),
            )
            existing = get_completed_run_by_fingerprint(
                self._db, organization_id=organization_id, fingerprint=fp
            )
            if existing and existing.status == ImportRunStatus.COMPLETED.value:
                raise ImportIdempotencyError(
                    f"Import déjà effectué (run={existing.id})"
                )
        except ImportNotFoundError:
            pass
        except ImportValidationError:
            # Session absente / non ready — laisse assert_document_importable décider
            pass

        item, session = assert_document_importable(
            self._db, organization_id=organization_id, document_id=document_id
        )
        fp = build_fingerprint(
            organization_id=organization_id,
            document_intake_item_id=document_id,
            validation_session_id=session.id,
            validation_version=int(session.version or 1),
        )
        existing = get_completed_run_by_fingerprint(
            self._db, organization_id=organization_id, fingerprint=fp
        )
        if existing and existing.status == ImportRunStatus.COMPLETED.value:
            raise ImportIdempotencyError(
                f"Import déjà effectué (run={existing.id})"
            )

        run = ElfisImportRun(
            organization_id=organization_id,
            migration_session_id=session.migration_session_id or item.migration_session_id,
            document_intake_item_id=document_id,
            universal_document_id=item.universal_document_id or session.universal_document_id,
            validation_session_id=session.id,
            validation_version=int(session.version or 1),
            extraction_id=session.extraction_id,
            status=ImportRunStatus.PENDING.value,
            fingerprint=fp,
            idempotency_key=build_idempotency_key(fp),
            actor_user_id=actor_user_id,
            started_at=datetime.utcnow(),
            progress_percent=0,
        )
        self._db.add(run)
        self._db.flush()
        write_import_audit(
            self._db,
            organization_id=organization_id,
            action="import_started",
            import_run_id=run.id,
            actor_user_id=actor_user_id,
        )
        self._db.commit()
        self._db.refresh(run)
        self._db.refresh(item)
        self._db.refresh(session)
        return self._pipeline.execute(
            run, item=item, session=session, actor_user_id=actor_user_id
        )

    def get_import(
        self, *, organization_id: int, import_id: str
    ) -> ElfisImportRun:
        run = self._repo.get_run(organization_id=organization_id, import_id=import_id)
        if not run:
            raise ImportNotFoundError()
        return run

    def list_imports(
        self,
        *,
        organization_id: int,
        migration_session_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ElfisImportRun], int]:
        return self._repo.list_runs(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            limit=limit,
            offset=offset,
        )

    def get_report(self, *, organization_id: int, import_id: str):
        run = self.get_import(organization_id=organization_id, import_id=import_id)
        report = self._repo.get_report(
            organization_id=organization_id, import_id=import_id
        )
        if not report:
            raise ImportNotFoundError("Rapport introuvable")
        return report

    def retry_import(
        self,
        *,
        organization_id: int,
        import_id: str,
        actor_user_id: int | None,
    ) -> ElfisImportRun:
        run = self.get_import(organization_id=organization_id, import_id=import_id)
        if run.status not in {
            ImportRunStatus.FAILED.value,
            ImportRunStatus.CANCELLED.value,
        }:
            raise ImportStateError("Seuls les imports failed/cancelled sont rejouables")
        # réutilise le même document — nouvelle tentative (nouvelle version fingerprint si validation inchangée → idempotence)
        return self.import_document(
            organization_id=organization_id,
            document_id=run.document_intake_item_id,
            actor_user_id=actor_user_id,
        )

    def rollback_import(
        self,
        *,
        organization_id: int,
        import_id: str,
        actor_user_id: int | None,
        reason: str | None = None,
    ) -> ElfisImportRun:
        run = self.get_import(organization_id=organization_id, import_id=import_id)
        if run.status not in {
            ImportRunStatus.COMPLETED.value,
            ImportRunStatus.FAILED.value,
        }:
            raise ImportStateError("Rollback impossible dans cet état")
        if run.status == ImportRunStatus.ROLLBACK_COMPLETED.value:
            raise ImportConflictError("Rollback déjà effectué")

        reason_code = reason or RollbackReason.MANUAL.value
        run.status = ImportRunStatus.ROLLING_BACK.value
        self._db.add(run)
        publish_import_event(
            self._db,
            event_type="rollback.started",
            run=run,
            actor_user_id=actor_user_id,
            metadata={"rollback_reason": reason_code},
        )
        write_import_audit(
            self._db,
            organization_id=organization_id,
            action="rollback_started",
            import_run_id=run.id,
            actor_user_id=actor_user_id,
            reason=reason_code,
        )
        self._db.flush()

        RollbackService(self._db).rollback_run(
            run, reason=reason_code, actor_user_id=actor_user_id
        )
        run.status = ImportRunStatus.ROLLBACK_COMPLETED.value
        self._db.add(run)

        from app.document_intake.models import ElfisDocumentIntakeItem

        item = (
            self._db.query(ElfisDocumentIntakeItem)
            .filter(ElfisDocumentIntakeItem.id == run.document_intake_item_id)
            .filter(ElfisDocumentIntakeItem.organization_id == organization_id)
            .first()
        )
        if item and item.lifecycle_status in {
            DocumentLifecycleStatus.IMPORT_COMPLETED.value,
            DocumentLifecycleStatus.IMPORTED.value,
            DocumentLifecycleStatus.IMPORTING.value,
            DocumentLifecycleStatus.IMPORT_FAILED.value,
        }:
            self._lifecycle.mark_rollback_completed(
                item,
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                reason_code=reason_code,
                commit=False,
            )

        publish_import_event(
            self._db,
            event_type="rollback.completed",
            run=run,
            actor_user_id=actor_user_id,
            metadata={"rollback_reason": reason_code},
        )
        write_import_audit(
            self._db,
            organization_id=organization_id,
            action="rollback_completed",
            import_run_id=run.id,
            actor_user_id=actor_user_id,
            reason=reason_code,
        )
        self._db.commit()
        self._db.refresh(run)
        return run
