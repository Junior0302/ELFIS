"""Modèles SQLAlchemy — Import Engine."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import JSON

from app.database import Base
from app.import_engine.enums import ImportRunStatus


def _uuid() -> str:
    return str(uuid4())


class ElfisImportRun(Base):
    __tablename__ = "elfis_import_runs"
    __table_args__ = (
        Index("ix_elfis_imp_org_created", "organization_id", "created_at"),
        Index("ix_elfis_imp_item", "document_intake_item_id"),
        Index("ix_elfis_imp_status", "organization_id", "status"),
        Index("ix_elfis_imp_mig", "migration_session_id"),
        Index(
            "ix_elfis_imp_doc_val_ver",
            "organization_id",
            "document_intake_item_id",
            "validation_session_id",
            "validation_version",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    migration_session_id = Column(String(36), nullable=True)
    document_intake_item_id = Column(
        String(36), ForeignKey("elfis_document_intake_items.id"), nullable=False
    )
    universal_document_id = Column(String(32), nullable=True)
    validation_session_id = Column(String(36), nullable=False)
    validation_version = Column(Integer, nullable=False, default=1)
    extraction_id = Column(String(36), nullable=True)
    schema_name = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default=ImportRunStatus.PENDING.value)
    fingerprint = Column(String(64), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    progress_percent = Column(Integer, nullable=False, default=0)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    warnings_json = Column("warnings", JSON, nullable=False, default=list)
    created_objects_json = Column("created_objects", JSON, nullable=False, default=list)
    linked_objects_json = Column("linked_objects", JSON, nullable=False, default=list)
    report_id = Column(String(36), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    rolled_back_at = Column(DateTime, nullable=True)
    rollback_reason = Column(String(64), nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ElfisImportFingerprint(Base):
    """Empreinte d'idempotence — même document + même validation = un seul import."""

    __tablename__ = "elfis_import_fingerprints"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "fingerprint",
            name="uq_elfis_imp_fp",
        ),
        Index("ix_elfis_imp_fp_run", "import_run_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    document_intake_item_id = Column(String(36), nullable=False)
    validation_session_id = Column(String(36), nullable=False)
    validation_version = Column(Integer, nullable=False)
    import_run_id = Column(String(36), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deactivated_at = Column(DateTime, nullable=True)


class ElfisImportArtifact(Base):
    """Objets créés / liés — nécessaires au rollback."""

    __tablename__ = "elfis_import_artifacts"
    __table_args__ = (
        Index("ix_elfis_imp_art_run", "import_run_id"),
        Index("ix_elfis_imp_art_entity", "entity_kind", "entity_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    import_run_id = Column(
        String(36), ForeignKey("elfis_import_runs.id"), nullable=False
    )
    entity_kind = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False)
    action = Column(String(32), nullable=False)  # created|linked|updated
    label = Column(String(255), nullable=True)
    snapshot_json = Column("snapshot", JSON, nullable=False, default=dict)
    rolled_back = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    rolled_back_at = Column(DateTime, nullable=True)


class ElfisImportReport(Base):
    """Rapport d'import versionné."""

    __tablename__ = "elfis_import_reports"
    __table_args__ = (
        Index("ix_elfis_imp_rep_run", "import_run_id"),
        UniqueConstraint("import_run_id", "version", name="uq_elfis_imp_rep_ver"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    import_run_id = Column(
        String(36), ForeignKey("elfis_import_runs.id"), nullable=False
    )
    version = Column(Integer, nullable=False, default=1)
    documents_json = Column("documents", JSON, nullable=False, default=list)
    created_objects_json = Column("created_objects", JSON, nullable=False, default=list)
    linked_objects_json = Column("linked_objects", JSON, nullable=False, default=list)
    warnings_json = Column("warnings", JSON, nullable=False, default=list)
    duration_ms = Column(Integer, nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    report_json = Column("report", JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ElfisImportAuditLog(Base):
    """Audit append-only."""

    __tablename__ = "elfis_import_audit_log"
    __table_args__ = (
        Index("ix_elfis_imp_audit_run", "import_run_id", "created_at"),
        Index("ix_elfis_imp_audit_org", "organization_id", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    import_run_id = Column(String(36), nullable=True)
    action = Column(String(64), nullable=False)
    entity_kind = Column(String(64), nullable=True)
    entity_id = Column(String(64), nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    detail_json = Column("detail", JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
