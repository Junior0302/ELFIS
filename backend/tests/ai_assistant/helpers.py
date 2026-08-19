"""Helpers tests AI Financial Assistant — réutilise le jeu de données financial."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai_assistant.observability import response_cache
from app.models_saas import User
from tests.financial.helpers import TODAY, make_financial_db, seed_finance_data, seed_org

__all__ = [
    "TODAY",
    "make_assistant_db",
    "seed_assistant",
]


def make_assistant_db() -> Session:
    db = make_financial_db()
    response_cache.clear()
    return db


def seed_assistant(db: Session) -> tuple:
    org = seed_org(db, "Org Assistant")
    seed_finance_data(db, org.id, today=TODAY)
    user = User(
        email="assistant@test.local",
        first_name="Ada",
        last_name="Finance",
        status="active",
        password_hash="x",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return org, user
