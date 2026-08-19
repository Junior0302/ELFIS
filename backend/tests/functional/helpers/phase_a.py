"""Helpers Phase A — JWT edge cases + seed ressources isolées."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from jose import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models_vault import VaultDocument
from app.services.auth import create_access_token


def mint_token(
    *,
    sub: str | int,
    org_id: int | None = None,
    expires_delta: timedelta | None = None,
    extra: dict[str, Any] | None = None,
    secret: str | None = None,
    algorithm: str = "HS256",
) -> str:
    payload: dict[str, Any] = {"sub": str(sub)}
    if org_id is not None:
        payload["org_id"] = org_id
    if extra:
        payload.update(extra)
    key = secret or settings.jwt_secret
    if expires_delta is not None:
        payload["exp"] = datetime.utcnow() + expires_delta
        return jwt.encode(payload, key, algorithm=algorithm)
    if secret is not None:
        payload["exp"] = datetime.utcnow() + timedelta(hours=1)
        return jwt.encode(payload, key, algorithm=algorithm)
    return create_access_token(payload)


def mint_expired_token(*, sub: str | int, org_id: int | None = None, expired_since: timedelta) -> str:
    payload: dict[str, Any] = {
        "sub": str(sub),
        "exp": datetime.utcnow() - expired_since,
    }
    if org_id is not None:
        payload["org_id"] = org_id
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def mint_nbf_token(*, sub: str | int, org_id: int | None, nbf_delta: timedelta) -> str:
    payload: dict[str, Any] = {
        "sub": str(sub),
        "exp": datetime.utcnow() + timedelta(hours=1),
        "nbf": datetime.utcnow() + nbf_delta,
    }
    if org_id is not None:
        payload["org_id"] = org_id
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def seed_vault_document(
    db: Session, *, org_id: int, doc_id: str | None = None, marker: str = "ALPHA"
) -> VaultDocument:
    now = datetime.utcnow()
    doc = VaultDocument(
        id=doc_id or str(uuid4()),
        organization_id=org_id,
        document_type="supplier_invoice",
        document_number=f"FAC-{marker}",
        original_filename=f"invoice_{marker}.pdf",
        storage_path=f"entreprises/{org_id}/2026/factures/{marker}.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum_sha256=f"checksum-{marker}-{uuid4().hex[:12]}",
        invoice_date=date(2026, 7, 1),
        amount_ht=Decimal("100.00"),
        amount_vat=Decimal("20.00"),
        amount_ttc=Decimal("120.00"),
        currency="EUR",
        archive_status="archived",
        accounting_status="not_processed",
        email_status="not_sent",
        version=1,
        archived_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def seed_search_document(db: Session, *, org_id: int, unique_term: str) -> Any:
    from app.search.search_models import ElfisSearchDocument

    now = datetime.utcnow()
    row = ElfisSearchDocument(
        id=str(uuid4()),
        search_document_id=str(uuid4()),
        organization_id=org_id,
        resource_type="vault_document",
        resource_id=str(uuid4()),
        resource_version=1,
        title=f"Doc {unique_term}",
        content=f"Fournisseur {unique_term} facture test",
        search_text=f"fournisseur {unique_term} facture test",
        action_url=f"/documents/{uuid4()}",
        metadata_json={"marker": unique_term},
        is_active=True,
        indexed_at=now,
        created_at=now,
        updated_at=now,
        content_hash=uuid4().hex,
    )
    db.add(row)
    db.commit()
    return row


def seed_notification(db: Session, *, org_id: int, user_id: int, title: str = "Notif Phase A") -> Any:
    from app.notifications.notification_models import ElfisNotification

    now = datetime.utcnow()
    row = ElfisNotification(
        id=str(uuid4()),
        notification_id=str(uuid4()),
        organization_id=org_id,
        user_id=user_id,
        notification_type="system.phase_a.v1",
        category="system",
        title=title,
        message="Message de recette Phase A",
        severity="info",
        status="unread",
        data={},
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def assert_safe_error_body(body: dict) -> None:
    blob = str(body).lower()
    for forbidden in (
        "traceback",
        "sqlalchemy",
        "jose.",
        "select ",
        "insert ",
        "bearer ",
        "sk_live",
        "c:\\users",
        "/home/",
        "password=",
    ):
        assert forbidden not in blob, f"fuite détectée: {forbidden}"
    assert "error" in body or "detail" in body
