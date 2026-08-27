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
from app.jobs import job_models  # noqa: F401
from app.banking.banking_types import (
    ConnectorHealth,
    NormalizedAccount,
    NormalizedTransaction,
    TransactionPage,
    TransactionStatus,
)
from app.banking.connectors.base import BankConnector, ConnectorError


def make_banking_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine), engine


def make_banking_db() -> Session:
    factory, _engine = make_banking_session_factory()
    return factory()


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
        page_size: int | None = None,
        fail_on_page: int | None = None,
        fail_status_code: int | None = None,
        repeat_cursor: bool = False,
        hold_before_page: object | None = None,
        release_before_page: object | None = None,
    ):
        self.accounts = accounts or [
            NormalizedAccount(
                external_id="fake-acc-1",
                label="Compte pro",
                bank_name="Banque Factice",
                iban="FR7699999000011234567890147",
                currency="EUR",
                balance=1000.0,
                available_balance=None,
                account_type="checking",
            )
        ]
        self.transactions = transactions or {}
        self.fail_times = fail_times
        self.fail_retryable = fail_retryable
        self.fail_on_account = fail_on_account
        self.page_size = page_size
        self.fail_on_page = fail_on_page
        self.fail_status_code = fail_status_code
        self.repeat_cursor = repeat_cursor
        self.hold_before_page = hold_before_page
        self.release_before_page = release_before_page
        self._page_calls: dict[str, int] = {}
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.refresh_calls = 0

    def connect(self, *, organization_id: int, bank_name: str, options: dict | None = None) -> str:
        self.connect_calls += 1
        return f"fake-conn-{organization_id}"

    def disconnect(self, provider_connection_id: str, *, organization_id: int | None = None) -> None:
        self.disconnect_calls += 1

    def refresh(self, provider_connection_id: str, *, organization_id: int | None = None) -> None:
        self.refresh_calls += 1

    def list_accounts(
        self, provider_connection_id: str, *, organization_id: int | None = None
    ) -> list[NormalizedAccount]:
        return list(self.accounts)

    def _filtered_rows(
        self, account_external_id: str, since: date | None
    ) -> list[NormalizedTransaction]:
        rows = self.transactions.get(account_external_id, [])
        if since:
            rows = [t for t in rows if t.booked_at > since]
        return list(rows)

    def _maybe_fail(self, account_external_id: str) -> None:
        if self.fail_times > 0 and (
            self.fail_on_account is None or account_external_id == self.fail_on_account
        ):
            self.fail_times -= 1
            raise ConnectorError(
                "Panne simulée du fournisseur",
                retryable=self.fail_retryable,
                status_code=self.fail_status_code,
            )

    def list_transactions(
        self,
        provider_connection_id: str,
        account_external_id: str,
        *,
        since: date | None = None,
        organization_id: int | None = None,
    ) -> list[NormalizedTransaction]:
        self._maybe_fail(account_external_id)
        return self._filtered_rows(account_external_id, since)

    def list_transaction_page(
        self,
        provider_connection_id: str,
        account_external_id: str,
        *,
        since: date | None = None,
        cursor: str | None = None,
        organization_id: int | None = None,
    ) -> TransactionPage:
        if self.hold_before_page is not None:
            self.hold_before_page.set()
            if self.release_before_page is not None:
                self.release_before_page.wait(timeout=15)
        if not cursor:
            self._page_calls[account_external_id] = 0
        page_no = self._page_calls.get(account_external_id, 0) + 1
        self._page_calls[account_external_id] = page_no
        if self.fail_on_page is not None and page_no == self.fail_on_page:
            raise ConnectorError("Panne simulée en pagination", retryable=True)
        self._maybe_fail(account_external_id)
        rows = self._filtered_rows(account_external_id, since)
        if self.page_size is None or self.page_size <= 0:
            return TransactionPage(transactions=rows, next_cursor=None, has_more=False)
        index = int(cursor or "0")
        start = index * self.page_size
        chunk = rows[start : start + self.page_size]
        has_more = start + self.page_size < len(rows)
        if self.repeat_cursor and has_more:
            return TransactionPage(
                transactions=chunk, next_cursor=str(index), has_more=True
            )
        return TransactionPage(
            transactions=chunk,
            next_cursor=str(index + 1) if has_more else None,
            has_more=has_more,
        )

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
    external_id: str | None = None,
    value_date: date | None = None,
    counterparty_name: str | None = None,
    reference: str | None = None,
) -> NormalizedTransaction:
    return NormalizedTransaction(
        external_id=external_id if external_id is not None else tx_id(account, booked, label, amount),
        booked_at=booked,
        value_date=value_date,
        label=label,
        amount=amount,
        currency="EUR",
        account_external_id=account,
        status=status,
        source=source,
        counterparty_name=counterparty_name,
        reference=reference,
    )
