"""Helpers SQLite — tests Document Intake."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.audit import audit_models  # noqa: F401
from app.database import Base
from app.document_intake import models as intake_models  # noqa: F401
from app.events import event_models  # noqa: F401
from app.migration_center import models as mig_models  # noqa: F401
from app.models_saas import Organization, User  # noqa: F401


def make_intake_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            Organization.__table__,
            audit_models.ElfisAuditEvent.__table__,
            event_models.ElfisEvent.__table__,
            event_models.ElfisEventDelivery.__table__,
            mig_models.ElfisMigrationSession.__table__,
            mig_models.ElfisMigrationTimelineEntry.__table__,
            mig_models.ElfisMigrationActivity.__table__,
            intake_models.ElfisDocumentDocIdCounter.__table__,
            intake_models.ElfisDocumentUploadSession.__table__,
            intake_models.ElfisDocumentIntakeItem.__table__,
            intake_models.ElfisDocumentLifecycleEntry.__table__,
        ],
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def factory():
        return Session()

    return factory, engine


def seed_org_user(db, *, email: str = "intake@test.local", name: str = "Org Intake"):
    org = Organization(name=name)
    db.add(org)
    db.flush()
    user = User(
        first_name="In",
        last_name="Take",
        email=email,
        password_hash="x",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(org)
    db.refresh(user)
    return org, user


PDF_MINIMAL = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
PNG_MINIMAL = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)
ZIP_MINIMAL = b"PK\x03\x04" + b"\x00" * 26 + b"PK\x05\x06" + b"\x00" * 18
