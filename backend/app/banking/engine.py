"""Banking Engine — unique source de vérité des données bancaires.

Gère banques connectées, comptes, IBAN, devises, soldes et historique.
Ne connaît aucun fournisseur : tout passe par le registre de connecteurs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.orm import Session

from app.banking.account_types import normalize_account_type
from app.banking.banking_models import ElfisBankConnection, ElfisBankSyncRun
from app.banking.banking_types import ConnectionStatus, NormalizedAccount
from app.banking.banking_events import publish_connection_event
from app.banking.consent_state import ConsentStateError, issue_consent_state, verify_consent_state
from app.banking.connectors.base import BankConnector, ConnectorError
from app.banking.connectors import registry
from app.banking.demo_gate import DEMO_PROVIDER, FICTIONAL_BANK_LABEL, is_demo_bank_enabled
from app.config import settings
from app.events.event_types import EventNames
from app.models import BankAccount, BankTransaction

logger = logging.getLogger(__name__)


def _callback_url_with_state(base: str, state: str) -> str:
    parts = urlsplit(base.strip())
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["state"] = state
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class BankingEngineError(Exception):
    pass


class SyncAlreadyInProgressError(BankingEngineError):
    """Une synchronisation de la même connexion est déjà en cours (verrou DB)."""


class BankingEngine:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # Connecteurs disponibles
    # ------------------------------------------------------------------ #

    def available_connectors(self) -> list[dict]:
        out: list[dict] = []
        for provider in registry.list_providers():
            if provider == DEMO_PROVIDER and not is_demo_bank_enabled():
                continue
            connector = registry.get_connector(provider)
            health = connector.health()
            fictional = provider == DEMO_PROVIDER
            out.append(
                {
                    "provider": provider,
                    "display_name": FICTIONAL_BANK_LABEL if fictional else connector.display_name,
                    "configured": health.configured,
                    "status": health.status,
                    "message": FICTIONAL_BANK_LABEL if fictional else health.message,
                    "latency_ms": health.latency_ms,
                    "requires_user_consent": bool(connector.requires_user_consent),
                    "fictional": fictional,
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
        if provider == DEMO_PROVIDER and not is_demo_bank_enabled():
            raise BankingEngineError("Banque Démo ELFIS désactivée.")
        connector = registry.get_connector(provider)
        if connector.requires_user_consent:
            raise BankingEngineError(
                "Ce fournisseur nécessite un consentement utilisateur. "
                "Utilisez le parcours de connexion redirigé."
            )
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
            accounts = connector.list_accounts(
                provider_connection_id, organization_id=organization_id
            )
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

    def begin_bank_consent(
        self,
        *,
        organization_id: int,
        provider: str,
        bank_name: str = "",
    ) -> tuple[ElfisBankConnection, str]:
        connector = registry.get_connector(provider)
        if not connector.requires_user_consent:
            raise BankingEngineError("Ce fournisseur ne nécessite pas de consentement redirigé.")
        callback_base = (settings.banking_bridge_redirect_uri or "").strip()
        if not callback_base:
            raise BankingEngineError(
                "Callback Bridge non configuré (BANKING_BRIDGE_REDIRECT_URI)."
            )

        self._supersede_pending_consents(organization_id, provider)
        connection = ElfisBankConnection(
            organization_id=organization_id,
            provider=provider,
            provider_connection_id="",
            bank_name=bank_name or connector.display_name,
            status=ConnectionStatus.preparing.value,
        )
        self.db.add(connection)
        self.db.flush()

        state = issue_consent_state(organization_id=organization_id, connection_id=connection.id)
        callback_url = _callback_url_with_state(callback_base, state)
        try:
            started = connector.start_user_consent(
                organization_id=organization_id,
                callback_url=callback_url,
                bank_name=bank_name,
                context=state,
            )
        except ConnectorError as exc:
            connection.status = ConnectionStatus.error.value
            connection.error_message = str(exc)
            self.db.add(connection)
            self.db.commit()
            raise
        connection.status = ConnectionStatus.awaiting_consent.value
        connection.error_message = None
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        logger.info(
            "banking_consent_started",
            extra={
                "organization_id": organization_id,
                "provider": provider,
                "connection_id": connection.id,
            },
        )
        return connection, started.redirect_url

    def finalize_bank_consent(
        self,
        *,
        state: str | None,
        context: str | None = None,
        item_id: str | None = None,
        success: str | None = None,
    ) -> str:
        """Valide le retour fournisseur. Retourne ok | denied | error."""
        token = (state or "").strip() or (context or "").strip()
        try:
            claims = verify_consent_state(token)
        except ConsentStateError:
            logger.warning("banking_consent_invalid_state")
            return "error"

        organization_id = claims["organization_id"]
        connection_id = claims["connection_id"]
        try:
            connection = self.get_connection(organization_id, connection_id)
        except BankingEngineError:
            logger.warning(
                "banking_consent_unknown_connection",
                extra={"organization_id": organization_id, "connection_id": connection_id},
            )
            return "error"

        if connection.status != ConnectionStatus.awaiting_consent.value:
            logger.warning(
                "banking_consent_replay_refused",
                extra={"organization_id": organization_id, "connection_id": connection.id},
            )
            return "error"

        accepted = str(success or "").strip().lower() in {"1", "true", "yes"}
        remote_item = str(item_id or "").strip()
        if not accepted or not remote_item:
            connection.status = ConnectionStatus.error.value
            connection.error_message = "Consentement bancaire annulé ou incomplet."
            self.db.add(connection)
            self.db.commit()
            return "denied"

        connector = self.get_connector_for(connection)
        try:
            completed = connector.complete_user_consent(
                organization_id=organization_id,
                provider_item_id=remote_item,
            )
        except ConnectorError as exc:
            connection.status = ConnectionStatus.error.value
            connection.error_message = str(exc)
            self.db.add(connection)
            self.db.commit()
            logger.warning(
                "banking_consent_item_rejected",
                extra={"organization_id": organization_id, "connection_id": connection.id},
            )
            return "error"

        connection.provider_connection_id = completed.provider_connection_id
        connection.bank_name = completed.bank_name or connection.bank_name
        connection.status = ConnectionStatus.connected.value
        connection.error_message = None
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)

        try:
            accounts = connector.list_accounts(
                connection.provider_connection_id,
                organization_id=organization_id,
            )
            self.upsert_accounts(connection, accounts)
        except ConnectorError as exc:
            logger.warning(
                "banking_connect_accounts_failed",
                extra={
                    "provider": connection.provider,
                    "connection_id": connection.id,
                    "error": str(exc),
                },
            )

        publish_connection_event(
            self.db,
            event_name=EventNames.BANKING_CONNECTION_CONNECTED,
            organization_id=organization_id,
            connection_id=connection.id,
            provider=connection.provider,
            bank_name=connection.bank_name,
        )
        logger.info(
            "banking_connection_connected",
            extra={
                "organization_id": organization_id,
                "provider": connection.provider,
                "connection_id": connection.id,
            },
        )

        from app.banking.sync_jobs import request_connection_sync

        try:
            request_connection_sync(
                self.db,
                organization_id=organization_id,
                connection_id=connection.id,
                trigger="consent",
            )
        except Exception as exc:
            logger.warning(
                "banking_consent_initial_sync_failed",
                extra={"connection_id": connection.id, "error": type(exc).__name__},
            )
        return "ok"

    def _supersede_pending_consents(self, organization_id: int, provider: str) -> None:
        pending = (
            self.db.query(ElfisBankConnection)
            .filter(
                ElfisBankConnection.organization_id == organization_id,
                ElfisBankConnection.provider == provider,
                ElfisBankConnection.status.in_(
                    [
                        ConnectionStatus.preparing.value,
                        ConnectionStatus.awaiting_consent.value,
                    ]
                ),
            )
            .all()
        )
        for row in pending:
            row.status = ConnectionStatus.error.value
            row.error_message = "Tentative remplacée par une nouvelle connexion."
            self.db.add(row)

    def disconnect(self, *, organization_id: int, connection_id: int) -> ElfisBankConnection:
        connection = self.get_connection(organization_id, connection_id)
        connector = self.get_connector_for(connection)
        try:
            if connection.provider_connection_id:
                connector.disconnect(
                    connection.provider_connection_id,
                    organization_id=organization_id,
                )
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
                account.available_balance = item.available_balance
                account.account_type = normalize_account_type(item.account_type)
                account.balance_updated_at = item.balance_updated_at
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
                    available_balance=item.available_balance,
                    account_type=normalize_account_type(item.account_type),
                    balance_updated_at=item.balance_updated_at,
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
            "connections_syncing": sum(
                1 for c in connections if (c.last_sync_status or "") == "syncing"
            ),
            "connections_needs_reauth": sum(
                1
                for c in connections
                if (c.last_sync_error_code or "")
                in {"invalid_credentials", "connection_revoked", "consent_expired"}
            ),
        }

    def schedule_next_sync(self, connection: ElfisBankConnection) -> None:
        connection.next_sync_at = datetime.utcnow() + timedelta(
            minutes=max(5, connection.sync_interval_minutes)
        )
        self.db.add(connection)
