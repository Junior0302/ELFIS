"""Helpers de test Banking Platform V1 — base SQLite mémoire + connecteurs de test."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import ClassVar

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app import models  # noqa: F401
from app import models_saas  # noqa: F401
from app.banking import banking_models  # noqa: F401
from app.events import event_models  # noqa: F401
from app.banking.banking_types import (
    ConnectorHealth,
    NormalizedAccount,
    NormalizedTransaction,
    TransactionStatus,
)
from app.banking.connectors.base import BankConnector, ConnectorError


def make_banking_db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_org(db: Session, name: str = "Org Test") -> models_saas.Organization:
    org = models_saas.Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def tx_id(account: str, booked: date, label: str, amount: float) -> str:
    raw = f"{account}|{booked.isoformat()}|{label}|{amount:.2f}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


class FakeBankConnector(BankConnector):
    """Connecteur de test paramétrable (données injectées, pannes simulées)."""

    provider: ClassVar[str] = "fake"
    display_name: ClassVar[str] = "Banque Factice"

    def __init__(
        self,
        *,
        accounts: list[NormalizedAccount] | None = None,
        transactions: dict[str, list[NormalizedTransaction]] | None = None,
        fail_times: int = 0,
        fail_retryable: bool = True,
        fail_on_account: str | None = None,
    ):
        self.accounts = accounts or [
            NormalizedAccount(
                external_id="fake-acc-1",
                label="Compte pro",
                bank_name="Banque Factice",
                iban="FR7699999000011234567890147",
                currency="EUR",
                balance=1000.0,
            )
        ]
        self.transactions = transactions or {}
        self.fail_times = fail_times
        self.fail_retryable = fail_retryable
        self.fail_on_account = fail_on_account
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.refresh_calls = 0

    def connect(self, *, organization_id: int, bank_name: str, options: dict | None = None) -> str:
        self.connect_calls += 1
        return f"fake-conn-{organization_id}"

    def disconnect(self, provider_connection_id: str) -> None:
        self.disconnect_calls += 1

    def refresh(self, provider_connection_id: str) -> None:
        self.refresh_calls += 1

    def list_accounts(self, provider_connection_id: str) -> list[NormalizedAccount]:
        return list(self.accounts)

    def list_transactions(
        self,
        provider_connection_id: str,
        account_external_id: str,
        *,
        since: date | None = None,
    ) -> list[NormalizedTransaction]:
        if self.fail_times > 0 and (
            self.fail_on_account is None or account_external_id == self.fail_on_account
        ):
            self.fail_times -= 1
            raise ConnectorError("Panne simulée du fournisseur", retryable=self.fail_retryable)
        rows = self.transactions.get(account_external_id, [])
        if since:
            rows = [t for t in rows if t.booked_at > since]
        return list(rows)

    def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            provider=self.provider, configured=True, status="ok", message="test"
        )


def make_tx(
    account: str,
    booked: date,
    label: str,
    amount: float,
    *,
    source: str = "fake",
    status: TransactionStatus = TransactionStatus.booked,
) -> NormalizedTransaction:
    return NormalizedTransaction(
        external_id=tx_id(account, booked, label, amount),
        booked_at=booked,
        label=label,
        amount=amount,
        currency="EUR",
        account_external_id=account,
        status=status,
        source=source,
    )
