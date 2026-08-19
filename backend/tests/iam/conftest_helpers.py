"""Helpers SQLite pour tests IAM persistants."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.iam import iam_models  # noqa: F401
from app.models_saas import User  # noqa: F401


def make_iam_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Tables minimales : users + IAM
    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            iam_models.ElfisPlatformRole.__table__,
            iam_models.ElfisPlatformPermission.__table__,
            iam_models.ElfisPlatformRolePermission.__table__,
            iam_models.ElfisPlatformUserRole.__table__,
        ],
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def factory():
        return Session()

    return factory, engine


def seed_user(db, *, email: str = "admin@test.local", is_platform_admin: bool = False) -> User:
    u = User(
        first_name="A",
        last_name="B",
        email=email,
        password_hash="x",
        status="active",
        is_platform_admin=is_platform_admin,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u
