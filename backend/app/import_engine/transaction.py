"""Gestion transactionnelle de l'import."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session


@contextmanager
def import_transaction(db: Session) -> Iterator[Session]:
    """
    Enveloppe atomique : flush pendant le travail, commit à la sortie,
    rollback complet en cas d'exception (aucune donnée orpheline).
    """
    nested = db.begin_nested() if db.in_transaction() else None
    try:
        yield db
        db.flush()
        if nested is not None:
            nested.commit()
        else:
            db.commit()
    except Exception:
        if nested is not None:
            nested.rollback()
        else:
            db.rollback()
        raise
