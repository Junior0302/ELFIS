"""Banking Engine — unique source de vérité des données bancaires.

Gère banques connectées, comptes, IBAN, devises, soldes et historique.
Ne connaît aucun fournisseur : tout passe par le registre de connecteurs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.banking.banking_models import ElfisBankConnection, ElfisBankSyncRun
from app.banking.banking_types import ConnectionStatus, NormalizedAccount
from app.banking.banking_events import publish_connection_event
from app.banking.connectors.base import BankConnector, ConnectorError
from app.banking.connectors import registry
from app.events.event_types import EventNames
from app.models import BankAccount, BankTransaction

logger = logging.getLogger(__name__)


class BankingEngineError(Exception):
    pass


class BankingEngine:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # Connecteurs disponibles
    # ------------------------------------------------------------------ #

    def available_connectors(self) -> list[dict]:
        out: list[dict] = []
        for provider in registry.list_providers():
            connector = registry.get_connector(provider)
            health = connector.health()
            out.append(
                {
                    "provider": provider,
                    "display_name": connector.display_name,
                    "configured": health.configured,
                    "status": health.status,
                    "message": health.message,
                    "latency_ms": health.latency_ms,
                }
            )
        return out

    def get_connector_for(self, connection: ElfisBankConnection) -> BankConnector:
        return registry.get_connector(connection.provider)

    # ------------------------------------------------------------------ #
    # Connexions
    # ------------------------------------------------------------------ #

    def list_connections(self, organization_id: int) -> list[ElfisBankConnection]:
        return (
            self.db.query(ElfisBankConnection)
            .filter(ElfisBankConnection.organization_id == organization_id)
            .order_by(ElfisBankConnection.id.asc())
            .all()
        )

    def get_connection(self, organization_id: int, connection_id: int) -> ElfisBankConnection:
        connection = (
            self.db.query(ElfisBankConnection)
            .filter(
                ElfisBankConnection.id == connection_id,
                ElfisBankConnection.organization_id == organization_id,
            )
            .first()
        )
        if not connection:
            raise BankingEngineError("Connexion bancaire introuvable.")
        return connection

    def connect(
        self,
        *,
        organization_id: int,
        provider: str,
        bank_name: str = "",
        options: dict | None = None,
    ) -> ElfisBankConnection:
        connector = registry.get_connector(provider)
        provider_connection_id = connector.connect(
            organization_id=organization_id,
            bank_name=bank_name,
            options=options,
        )
        connection = (
            self.db.query(ElfisBankConnection)
            .filter(
                ElfisBankConnection.organization_id == organization_id,
                ElfisBankConnection.provider == provider,
                ElfisBankConnection.provider_connection_id == provider_connection_id,
            )
            .first()
        )
        if connection:
            connection.status = ConnectionStatus.connected.value
            connection.error_message = None
            connection.bank_name = bank_name or connection.bank_name
        else:
            connection = ElfisBankConnection(
                organization_id=organization_id,
                provider=provider,
                provider_connection_id=provider_connection_id,
                bank_name=bank_name or connector.display_name,
                status=ConnectionStatus.connected.value,
            )
            self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)

        # Importer immédiatement les comptes (source de vérité locale)
        try:
            accounts = connector.list_accounts(provider_connection_id)
            self.upsert_accounts(connection, accounts)
        except ConnectorError as exc:
            logger.warning(
                "banking_connect_accounts_failed",
                extra={"provider": provider, "connection_id": connection.id, "error": str(exc)},
            )

        publish_connection_event(
            self.db,
            event_name=EventNames.BANKING_CONNECTION_CONNECTED,
            organization_id=organization_id,
            connection_id=connection.id,
            provider=provider,
            bank_name=connection.bank_name,
        )
        logger.info(
            "banking_connection_connected",
            extra={
                "organization_id": organization_id,
                "provider": provider,
                "connection_id": connection.id,
            },
        )
        return connection

    def disconnect(self, *, organization_id: int, connection_id: int) -> ElfisBankConnection:
        connection = self.get_connection(organization_id, connection_id)
        connector = self.get_connector_for(connection)
        try:
            connector.disconnect(connection.provider_connection_id)
        except ConnectorError as exc:
            # La déconnexion locale prime : on journalise sans bloquer.
            logger.warning(
                "banking_provider_disconnect_failed",
                extra={"connection_id": connection.id, "error": str(exc)},
            )
        connection.status = ConnectionStatus.disconnected.value
        connection.next_sync_at = None
        for account in self.accounts_for_connection(connection):
            account.connected = False
            self.db.add(account)
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        publish_connection_event(
            self.db,
            event_name=EventNames.BANKING_CONNECTION_DISCONNECTED,
            organization_id=organization_id,
            connection_id=connection.id,
            provider=connection.provider,
            bank_name=connection.bank_name,
        )
        logger.info(
            "banking_connection_disconnected",
            extra={"organization_id": organization_id, "connection_id": connection.id},
        )
        return connection

    # ------------------------------------------------------------------ #
    # Comptes
    # ------------------------------------------------------------------ #

    def accounts_for_connection(self, connection: ElfisBankConnection) -> list[BankAccount]:
        return (
            self.db.query(BankAccount)
            .filter(BankAccount.connection_id == connection.id)
            .order_by(BankAccount.id.asc())
            .all()
        )

    def upsert_accounts(
        self, connection: ElfisBankConnection, normalized: list[NormalizedAccount]
    ) -> list[BankAccount]:
        result: list[BankAccount] = []
        for item in normalized:
            account = (
                self.db.query(BankAccount)
                .filter(
                    BankAccount.organization_id == connection.organization_id,
                    BankAccount.connection_id == connection.id,
                    BankAccount.external_id == item.external_id,
                )
                .first()
            )
            if account:
                account.label = item.label or account.label
                account.bank_name = item.bank_name or account.bank_name
                account.iban = item.iban or account.iban
                account.currency = item.currency or account.currency
                account.balance = float(item.balance)
                account.connected = True
            else:
                account = BankAccount(
                    organization_id=connection.organization_id,
                    connection_id=connection.id,
                    provider=connection.provider,
                    external_id=item.external_id,
                    label=item.label,
                    bank_name=item.bank_name or connection.bank_name,
                    iban=item.iban,
                    currency=item.currency,
                    balance=float(item.balance),
                    connected=True,
                )
                self.db.add(account)
            result.append(account)
        self.db.commit()
        for account in result:
            self.db.refresh(account)
        return result

    def list_accounts(self, organization_id: int) -> list[BankAccount]:
        return (
            self.db.query(BankAccount)
            .filter(BankAccount.organization_id == organization_id)
            .order_by(BankAccount.id.asc())
            .all()
        )

    # ------------------------------------------------------------------ #
    # Transactions (historique normalisé)
    # ------------------------------------------------------------------ #

    def list_transactions(
        self,
        organization_id: int,
        *,
        account_id: int | None = None,
        category: str | None = None,
        status: str | None = None,
        source: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[BankTransaction], int]:
        account_ids = [a.id for a in self.list_accounts(organization_id)]
        if not account_ids:
            return [], 0
        query = self.db.query(BankTransaction).filter(
            BankTransaction.account_id.in_(account_ids)
        )
        if account_id is not None:
            if account_id not in account_ids:
                return [], 0
            query = query.filter(BankTransaction.account_id == account_id)
        if category:
            query = query.filter(BankTransaction.category == category)
        if status:
            query = query.filter(BankTransaction.status == status)
        if source:
            query = query.filter(BankTransaction.source == source)
        if search:
            query = query.filter(BankTransaction.label.ilike(f"%{search.strip()}%"))
        total = query.count()
        rows = (
            query.order_by(BankTransaction.booked_at.desc(), BankTransaction.id.desc())
            .offset(max(offset, 0))
            .limit(max(1, min(limit, 500)))
            .all()
        )
        return rows, total

    # ------------------------------------------------------------------ #
    # Statut global
    # ------------------------------------------------------------------ #

    def status(self, organization_id: int) -> dict:
        connections = self.list_connections(organization_id)
        accounts = self.list_accounts(organization_id)
        account_ids = [a.id for a in accounts]
        tx_count = (
            self.db.query(BankTransaction)
            .filter(BankTransaction.account_id.in_(account_ids))
            .count()
            if account_ids
            else 0
        )
        last_run = (
            self.db.query(ElfisBankSyncRun)
            .filter(ElfisBankSyncRun.organization_id == organization_id)
            .order_by(ElfisBankSyncRun.started_at.desc())
            .first()
        )
        balances: dict[str, float] = {}
        for account in accounts:
            balances[account.currency] = round(
                balances.get(account.currency, 0.0) + float(account.balance), 2
            )
        return {
            "connections_total": len(connections),
            "connections_connected": sum(
                1 for c in connections if c.status == ConnectionStatus.connected.value
            ),
            "connections_error": sum(
                1 for c in connections if c.status == ConnectionStatus.error.value
            ),
            "accounts_total": len(accounts),
            "transactions_total": tx_count,
            "balances_by_currency": balances,
            "last_sync_at": last_run.started_at if last_run else None,
            "last_sync_status": last_run.status if last_run else None,
            "next_sync_at": min(
                (c.next_sync_at for c in connections if c.next_sync_at), default=None
            ),
        }

    def schedule_next_sync(self, connection: ElfisBankConnection) -> None:
        connection.next_sync_at = datetime.utcnow() + timedelta(
            minutes=max(5, connection.sync_interval_minutes)
        )
        self.db.add(connection)
