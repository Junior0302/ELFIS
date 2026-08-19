"""Helpers SQLite — tests Migration Center."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.audit import audit_models  # noqa: F401
from app.database import Base
from app.events import event_models  # noqa: F401
from app.migration_center import models as mig_models  # noqa: F401
from app.models_saas import Organization, User  # noqa: F401


class FakeAudit:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def __getattr__(self, name: str):
        if name.startswith("record_"):

            def _rec(**kwargs):
                self.events.append((name, kwargs))

            return _rec
        raise AttributeError(name)


def make_migration_db():
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
            mig_models.ElfisMigrationMemoryEntry.__table__,
        ],
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def factory():
        return Session()

    return factory, engine


def seed_org_user(db, *, email: str = "mig@test.local", name: str = "Org Mig"):
    org = Organization(name=name)
    db.add(org)
    db.flush()
    user = User(
        first_name="M",
        last_name="Ig",
        email=email,
        password_hash="x",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(org)
    db.refresh(user)
    return org, user


def valid_profile(**overrides):
    base = {
        "company_age_range": "more_than_2_years",
        "legal_form": "sas",
        "team_size": "two_to_five",
        "accountant_status": "has_accountant",
        "join_reasons": ["changing_software", "saving_time"],
    }
    base.update(overrides)
    return base
