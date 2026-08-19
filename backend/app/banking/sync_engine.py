"""Sync Engine — synchronisation fiable des transactions bancaires.

Gère :
- première importation (initial) et synchronisation incrémentale
- détection des doublons (external_id + empreinte montant/libellé/date)
- retry automatique (erreurs fournisseur transitoires)
- reprise après erreur (curseur persisté dans le journal)
- journalisation complète (ElfisBankSyncRun)
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.banking.banking_events import (
    publish_sync_completed,
    publish_sync_failed,
    publish_transaction_created,
    publish_transaction_updated,
)
from app.banking.banking_models import ElfisBankConnection, ElfisBankSyncRun
from app.banking.banking_types import (
    ConnectionStatus,
    NormalizedTransaction,
    SyncRunStatus,
    SyncType,
)
from app.banking.connectors.base import ConnectorError
from app.banking.engine import BankingEngine, BankingEngineError
from app.models import BankAccount, BankTransaction
from app.services.banking import categorize

logger = logging.getLogger(__name__)


class SyncEngine:
    def __init__(
        self,
        db: Session,
        *,
        max_attempts: int | None = None,
        retry_delay_seconds: float = 0.0,
    ):
        from app.config import settings

        self.db = db
        self.engine = BankingEngine(db)
        self.max_attempts = max(1, max_attempts or settings.banking_sync_max_attempts)
        self.retry_delay_seconds = max(0.0, retry_delay_seconds)

    # ------------------------------------------------------------------ #
    # API publique
    # ------------------------------------------------------------------ #

    def run_sync(
        self,
        organization_id: int,
        *,
        connection_id: int | None = None,
        trigger: str = "manual",
    ) -> list[ElfisBankSyncRun]:
        if connection_id is not None:
            connections = [self.engine.get_connection(organization_id, connection_id)]
        else:
            connections = [
                c
                for c in self.engine.list_connections(organization_id)
                if c.status != ConnectionStatus.disconnected.value
            ]
        if not connections:
            raise BankingEngineError(
                "Aucune connexion bancaire active. Connectez d'abord une banque."
            )
        return [self._sync_connection(c, trigger=trigger) for c in connections]

    def list_runs(
        self, organization_id: int, *, connection_id: int | None = None, limit: int = 50
    ) -> list[ElfisBankSyncRun]:
        query = self.db.query(ElfisBankSyncRun).filter(
            ElfisBankSyncRun.organization_id == organization_id
        )
        if connection_id is not None:
            query = query.filter(ElfisBankSyncRun.connection_id == connection_id)
        return (
            query.order_by(ElfisBankSyncRun.started_at.desc())
            .limit(max(1, min(limit, 200)))
            .all()
        )

    # ------------------------------------------------------------------ #
    # Synchronisation d'une connexion
    # ------------------------------------------------------------------ #

    def _sync_connection(
        self, connection: ElfisBankConnection, *, trigger: str
    ) -> ElfisBankSyncRun:
        if connection.status == ConnectionStatus.disconnected.value:
            raise BankingEngineError("Connexion déconnectée : reconnectez la banque.")

        previous_runs = (
            self.db.query(ElfisBankSyncRun)
            .filter(ElfisBankSyncRun.connection_id == connection.id)
            .order_by(ElfisBankSyncRun.started_at.desc())
            .all()
        )
        has_completed = any(r.status == SyncRunStatus.completed.value for r in previous_runs)
        sync_type = SyncType.incremental if has_completed else SyncType.initial
        last_run = previous_runs[0] if previous_runs else None
        inherited_cursor = next((r.cursor for r in previous_runs if r.cursor), None)
        resumed = bool(
            last_run
            and last_run.status == SyncRunStatus.failed.value
            and inherited_cursor is not None
        )

        run = ElfisBankSyncRun(
            organization_id=connection.organization_id,
            connection_id=connection.id,
            provider=connection.provider,
            sync_type=sync_type.value,
            trigger=trigger,
            status=SyncRunStatus.running.value,
            max_attempts=self.max_attempts,
            cursor=inherited_cursor,
            resumed_from_cursor=resumed,
            correlation_id=str(uuid.uuid4()),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        logger.info(
            "banking_sync_started",
            extra={
                "run_id": run.id,
                "organization_id": connection.organization_id,
                "connection_id": connection.id,
                "provider": connection.provider,
                "sync_type": run.sync_type,
                "resumed_from_cursor": run.resumed_from_cursor,
                "correlation_id": run.correlation_id,
            },
        )

        started = time.monotonic()
        last_error: ConnectorError | None = None
        for attempt in range(1, self.max_attempts + 1):
            run.attempt_count = attempt
            try:
                self._execute_attempt(connection, run)
                self._finalize_success(connection, run, started)
                return run
            except ConnectorError as exc:
                last_error = exc
                logger.warning(
                    "banking_sync_attempt_failed",
                    extra={
                        "run_id": run.id,
                        "attempt": attempt,
                        "retryable": exc.retryable,
                        "error": str(exc),
                        "correlation_id": run.correlation_id,
                    },
                )
                if not exc.retryable or attempt >= self.max_attempts:
                    break
                if self.retry_delay_seconds:
                    time.sleep(self.retry_delay_seconds)

        self._finalize_failure(connection, run, started, last_error)
        return run

    def _execute_attempt(self, connection: ElfisBankConnection, run: ElfisBankSyncRun) -> None:
        connector = self.engine.get_connector_for(connection)
        connector.refresh(connection.provider_connection_id)
        accounts = self.engine.upsert_accounts(
            connection, connector.list_accounts(connection.provider_connection_id)
        )
        run.accounts_synced = len(accounts)

        since = self._cursor_to_date(run.cursor) if run.sync_type == SyncType.incremental.value or run.resumed_from_cursor else None
        for account in accounts:
            transactions = connector.list_transactions(
                connection.provider_connection_id,
                account.external_id,
                since=since,
            )
            self._apply_transactions(account, transactions, run)
            account.last_sync_at = datetime.utcnow()
            self.db.add(account)
            # Curseur persisté après chaque compte : reprise possible en cas d'échec.
            self.db.add(run)
            self.db.commit()

    def _apply_transactions(
        self,
        account: BankAccount,
        transactions: list[NormalizedTransaction],
        run: ElfisBankSyncRun,
    ) -> None:
        existing = {
            tx.external_id: tx
            for tx in self.db.query(BankTransaction)
            .filter(BankTransaction.account_id == account.id)
            .all()
        }
        fingerprints = {
            (round(tx.amount, 2), tx.label.strip().lower(), tx.booked_at)
            for tx in existing.values()
        }
        max_booked = self._cursor_to_date(run.cursor)
        for item in sorted(transactions, key=lambda t: t.booked_at):
            booked_iso = item.booked_at.isoformat()
            current = existing.get(item.external_id)
            if current:
                if (
                    round(current.amount, 2) != round(item.amount, 2)
                    or current.label != item.label
                    or current.status != item.status.value
                ):
                    current.amount = round(item.amount, 2)
                    current.label = item.label
                    current.status = item.status.value
                    current.category = item.category or categorize(item.label)
                    self.db.add(current)
                    self.db.commit()
                    run.transactions_updated += 1
                    publish_transaction_updated(
                        self.db,
                        current,
                        organization_id=account.organization_id,
                        correlation_id=run.correlation_id,
                    )
                else:
                    run.duplicates_skipped += 1
            else:
                fingerprint = (round(item.amount, 2), item.label.strip().lower(), booked_iso)
                if fingerprint in fingerprints:
                    run.duplicates_skipped += 1
                    continue
                tx = BankTransaction(
                    account_id=account.id,
                    external_id=item.external_id,
                    booked_at=booked_iso,
                    label=item.label,
                    amount=round(item.amount, 2),
                    currency=item.currency,
                    category=item.category or categorize(item.label),
                    status=item.status.value,
                    source=item.source,
                )
                self.db.add(tx)
                self.db.commit()
                self.db.refresh(tx)
                existing[item.external_id] = tx
                fingerprints.add(fingerprint)
                run.transactions_created += 1
                publish_transaction_created(
                    self.db,
                    tx,
                    organization_id=account.organization_id,
                    correlation_id=run.correlation_id,
                )
            if max_booked is None or item.booked_at > max_booked:
                max_booked = item.booked_at
        if max_booked is not None:
            run.cursor = max_booked.isoformat()

    # ------------------------------------------------------------------ #
    # Finalisation
    # ------------------------------------------------------------------ #

    def _finalize_success(
        self, connection: ElfisBankConnection, run: ElfisBankSyncRun, started: float
    ) -> None:
        run.status = SyncRunStatus.completed.value
        run.finished_at = datetime.utcnow()
        run.duration_ms = round((time.monotonic() - started) * 1000, 2)
        run.error_message = None
        connection.status = ConnectionStatus.connected.value
        connection.error_message = None
        connection.last_sync_at = datetime.utcnow()
        self.engine.schedule_next_sync(connection)
        self.db.add(run)
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(run)
        publish_sync_completed(
            self.db,
            organization_id=run.organization_id,
            run_id=run.id,
            connection_id=connection.id,
            provider=connection.provider,
            sync_type=run.sync_type,
            transactions_created=run.transactions_created,
            transactions_updated=run.transactions_updated,
            duplicates_skipped=run.duplicates_skipped,
            duration_ms=run.duration_ms,
            correlation_id=run.correlation_id,
        )
        logger.info(
            "banking_sync_completed",
            extra={
                "run_id": run.id,
                "created": run.transactions_created,
                "updated": run.transactions_updated,
                "duplicates": run.duplicates_skipped,
                "duration_ms": run.duration_ms,
                "correlation_id": run.correlation_id,
            },
        )

    def _finalize_failure(
        self,
        connection: ElfisBankConnection,
        run: ElfisBankSyncRun,
        started: float,
        error: ConnectorError | None,
    ) -> None:
        message = str(error) if error else "Erreur de synchronisation inconnue"
        run.status = SyncRunStatus.failed.value
        run.finished_at = datetime.utcnow()
        run.duration_ms = round((time.monotonic() - started) * 1000, 2)
        run.error_message = message
        connection.status = ConnectionStatus.error.value
        connection.error_message = message
        self.db.add(run)
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(run)
        publish_sync_failed(
            self.db,
            organization_id=run.organization_id,
            run_id=run.id,
            connection_id=connection.id,
            provider=connection.provider,
            error_message=message,
            correlation_id=run.correlation_id,
        )
        logger.error(
            "banking_sync_failed",
            extra={
                "run_id": run.id,
                "attempts": run.attempt_count,
                "error": message,
                "correlation_id": run.correlation_id,
            },
        )

    @staticmethod
    def _cursor_to_date(cursor: str | None) -> date | None:
        if not cursor:
            return None
        try:
            return date.fromisoformat(cursor)
        except ValueError:
            return None
