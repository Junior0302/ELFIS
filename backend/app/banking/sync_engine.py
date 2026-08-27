"""Sync Engine — synchronisation fiable des transactions bancaires.

Gère :
- première importation (initial) et synchronisation incrémentale
- identité primaire provider (account + external_id)
- empreinte métier uniquement comme candidat (jamais une suppression)
- pagination fournisseur opaque + garde-fous
- retry automatique (erreurs fournisseur transitoires)
- reprise après erreur (curseur incrémental persisté, pas le curseur de page)
- journalisation complète (ElfisBankSyncRun)
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy.exc import IntegrityError
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
from app.banking.engine import BankingEngine, BankingEngineError, SyncAlreadyInProgressError
from app.banking.sync_lock import acquire_connection_sync_lock, release_connection_sync_lock
from app.banking.transaction_identity import business_fingerprint, provider_transaction_id
from app.banking.sync_status import mark_sync_failed, mark_sync_started, mark_sync_success
from app.banking.errors import classify_connector_error, public_sync_error_message
from app.models import BankAccount, BankTransaction
from app.observability.metrics import metrics_registry
from app.services.banking import categorize

logger = logging.getLogger(__name__)


class SyncEngine:
    def __init__(
        self,
        db: Session,
        *,
        max_attempts: int | None = None,
        retry_delay_seconds: float = 0.0,
        lock_wait_seconds: float | None = None,
    ):
        from app.config import settings

        self.db = db
        self.engine = BankingEngine(db)
        self.max_attempts = max(1, max_attempts or settings.banking_sync_max_attempts)
        self.retry_delay_seconds = max(0.0, retry_delay_seconds)
        self.max_pages = max(1, int(getattr(settings, "banking_sync_max_pages", 50) or 50))
        self.max_transactions = max(
            1, int(getattr(settings, "banking_sync_max_transactions_per_run", 10000) or 10000)
        )
        self.overlap_days = max(0, int(getattr(settings, "banking_sync_overlap_days", 7) or 0))
        self.run_timeout_seconds = max(
            1, int(getattr(settings, "banking_sync_run_timeout_seconds", 180) or 180)
        )
        configured_wait = getattr(settings, "banking_sync_lock_wait_seconds", 2.0)
        self.lock_wait_seconds = max(
            0.0,
            float(lock_wait_seconds if lock_wait_seconds is not None else configured_wait or 0.0),
        )

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
                if c.status
                in {ConnectionStatus.connected.value, ConnectionStatus.error.value}
                and (c.provider_connection_id or "").strip()
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
        if connection.status not in {
            ConnectionStatus.connected.value,
            ConnectionStatus.error.value,
        } or not (connection.provider_connection_id or "").strip():
            raise BankingEngineError(
                "Connexion bancaire non prête : le consentement doit d'abord aboutir."
            )

        held = acquire_connection_sync_lock(
            self.db,
            organization_id=connection.organization_id,
            connection_id=connection.id,
            wait_seconds=self.lock_wait_seconds,
        )
        if held is None:
            raise SyncAlreadyInProgressError(
                "Une synchronisation est déjà en cours pour cette connexion bancaire."
            )
        try:
            return self._sync_connection_locked(connection, trigger=trigger)
        finally:
            release_connection_sync_lock(held)

    def _sync_connection_locked(
        self, connection: ElfisBankConnection, *, trigger: str
    ) -> ElfisBankSyncRun:
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
                "trigger": trigger,
                "sync_type": run.sync_type,
                "resumed_from_cursor": run.resumed_from_cursor,
                "correlation_id": run.correlation_id,
            },
        )
        mark_sync_started(connection)
        self.db.add(connection)
        self.db.commit()

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
        org_id = connection.organization_id
        connector.refresh(connection.provider_connection_id, organization_id=org_id)
        accounts = self.engine.upsert_accounts(
            connection,
            connector.list_accounts(
                connection.provider_connection_id, organization_id=org_id
            ),
        )
        run.accounts_synced = len(accounts)

        since = self._incremental_since(run)
        imported = 0
        attempt_started = time.monotonic()
        for account in accounts:
            if account.organization_id != run.organization_id:
                raise ConnectorError(
                    "Isolation tenant : compte hors organisation.",
                    retryable=False,
                )
            imported += self._sync_account_pages(
                connector,
                connection,
                account,
                run,
                since=since,
                imported_so_far=imported,
                attempt_started=attempt_started,
            )
            account.last_sync_at = datetime.utcnow()
            self.db.add(account)
            # Curseur incrémental persisté après chaque compte : reprise possible.
            self.db.add(run)
            self.db.commit()

    def _incremental_since(self, run: ElfisBankSyncRun) -> date | None:
        cursor_date = self._cursor_to_date(run.cursor)
        if cursor_date is None:
            return None
        if run.sync_type != SyncType.incremental.value and not run.resumed_from_cursor:
            return None
        return cursor_date - timedelta(days=self.overlap_days)

    def _sync_account_pages(
        self,
        connector,
        connection: ElfisBankConnection,
        account: BankAccount,
        run: ElfisBankSyncRun,
        *,
        since: date | None,
        imported_so_far: int,
        attempt_started: float,
    ) -> int:
        seen_cursors: set[str] = set()
        cursor: str | None = None
        imported = 0
        for page_index in range(1, self.max_pages + 1):
            if time.monotonic() - attempt_started > self.run_timeout_seconds:
                raise ConnectorError("Délai de synchronisation dépassé.", retryable=True)
            page = connector.list_transaction_page(
                connection.provider_connection_id,
                account.external_id,
                since=since,
                cursor=cursor,
                organization_id=run.organization_id,
            )
            batch = list(page.transactions or [])
            if imported_so_far + imported + len(batch) > self.max_transactions:
                raise ConnectorError(
                    "Nombre maximal de transactions atteint pour ce run.",
                    retryable=False,
                )
            self._apply_transactions(account, batch, run)
            imported += len(batch)
            self.db.add(run)
            self.db.commit()
            if not page.has_more:
                return imported
            next_cursor = (page.next_cursor or "").strip()
            if not next_cursor:
                raise ConnectorError(
                    "Pagination incohérente : has_more sans curseur.",
                    retryable=False,
                )
            if next_cursor == (cursor or "") or next_cursor in seen_cursors:
                raise ConnectorError(
                    "Pagination incohérente : curseur répété.",
                    retryable=False,
                )
            seen_cursors.add(next_cursor)
            cursor = next_cursor
            if page_index >= self.max_pages:
                raise ConnectorError(
                    "Nombre maximal de pages atteint pour ce run.",
                    retryable=False,
                )
        raise ConnectorError("Nombre maximal de pages atteint pour ce run.", retryable=False)

    def _apply_transactions(
        self,
        account: BankAccount,
        transactions: list[NormalizedTransaction],
        run: ElfisBankSyncRun,
    ) -> None:
        rows = (
            self.db.query(BankTransaction)
            .filter(BankTransaction.account_id == account.id)
            .all()
        )
        fingerprints = {
            business_fingerprint(tx.amount, tx.label, tx.booked_at) for tx in rows
        }
        max_booked = self._cursor_to_date(run.cursor)
        for item in sorted(transactions, key=lambda t: t.booked_at):
            booked_iso = item.booked_at.isoformat()
            provider_id = provider_transaction_id(item.external_id)
            if provider_id:
                outcome = self._upsert_provider_transaction(
                    account, item, booked_iso, run, fingerprints
                )
            else:
                outcome = self._insert_observation(
                    account, item, booked_iso, provider_id, run, fingerprints
                )
            if outcome == "created":
                fingerprints.add(
                    business_fingerprint(item.amount, item.label, booked_iso)
                )
            if max_booked is None or item.booked_at > max_booked:
                max_booked = item.booked_at
        if max_booked is not None:
            run.cursor = max_booked.isoformat()

    def _find_by_provider_id(
        self, account_id: int, provider_id: str
    ) -> BankTransaction | None:
        provider_id = provider_transaction_id(provider_id)
        if not provider_id:
            return None
        return (
            self.db.query(BankTransaction)
            .filter(
                BankTransaction.account_id == account_id,
                BankTransaction.external_id == provider_id,
            )
            .one_or_none()
        )

    def _upsert_provider_transaction(
        self,
        account: BankAccount,
        item: NormalizedTransaction,
        booked_iso: str,
        run: ElfisBankSyncRun,
        fingerprints: set,
    ) -> str:
        provider_id = provider_transaction_id(item.external_id)
        current = self._find_by_provider_id(account.id, provider_id)
        if current is not None:
            return self._update_existing(current, item, booked_iso, account, run)

        tx = self._new_row(account, item, booked_iso, provider_id, fingerprints)
        try:
            with self.db.begin_nested():
                self.db.add(tx)
                self.db.flush()
        except IntegrityError:
            if tx in self.db:
                self.db.expunge(tx)
            with self.db.no_autoflush:
                current = self._find_by_provider_id(account.id, provider_id)
            if current is None:
                raise
            return self._update_existing(current, item, booked_iso, account, run)
        self.db.commit()
        persisted = self._find_by_provider_id(account.id, provider_id)
        if persisted is None:
            raise RuntimeError("Insert provider transaction introuvable après commit.")
        tx = persisted
        run.transactions_created += 1
        publish_transaction_created(
            self.db,
            tx,
            organization_id=account.organization_id,
            correlation_id=run.correlation_id,
        )
        return "created"

    def _insert_observation(
        self,
        account: BankAccount,
        item: NormalizedTransaction,
        booked_iso: str,
        provider_id: str,
        run: ElfisBankSyncRun,
        fingerprints: set,
    ) -> str:
        tx = self._new_row(account, item, booked_iso, provider_id, fingerprints)
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)
        run.transactions_created += 1
        publish_transaction_created(
            self.db,
            tx,
            organization_id=account.organization_id,
            correlation_id=run.correlation_id,
        )
        return "created"

    def _new_row(
        self,
        account: BankAccount,
        item: NormalizedTransaction,
        booked_iso: str,
        provider_id: str,
        fingerprints: set,
    ) -> BankTransaction:
        fingerprint = business_fingerprint(item.amount, item.label, booked_iso)
        return BankTransaction(
            account_id=account.id,
            external_id=provider_id,
            booked_at=booked_iso,
            value_date=item.value_date.isoformat() if item.value_date else None,
            label=item.label,
            amount=round(item.amount, 2),
            currency=item.currency,
            category=item.category or categorize(item.label),
            status=item.status.value,
            source=item.source,
            counterparty_name=item.counterparty_name,
            reference=item.reference,
            is_duplicate=fingerprint in fingerprints,
        )

    def _update_existing(
        self,
        current: BankTransaction,
        item: NormalizedTransaction,
        booked_iso: str,
        account: BankAccount,
        run: ElfisBankSyncRun,
    ) -> str:
        if self._apply_update(current, item, booked_iso):
            self.db.add(current)
            self.db.commit()
            run.transactions_updated += 1
            publish_transaction_updated(
                self.db,
                current,
                organization_id=account.organization_id,
                correlation_id=run.correlation_id,
            )
            return "updated"
        run.duplicates_skipped += 1
        return "unchanged"

    @staticmethod
    def _apply_update(current: BankTransaction, item: NormalizedTransaction, booked_iso: str) -> bool:
        value_iso = item.value_date.isoformat() if item.value_date else None
        new_amount = round(item.amount, 2)
        new_status = item.status.value
        changed = (
            round(current.amount, 2) != new_amount
            or current.label != item.label
            or current.status != new_status
            or current.booked_at != booked_iso
            or getattr(current, "value_date", None) != value_iso
            or getattr(current, "counterparty_name", None) != item.counterparty_name
            or getattr(current, "reference", None) != item.reference
            or current.currency != item.currency
        )
        if not changed:
            return False
        current.amount = new_amount
        current.label = item.label
        current.status = new_status
        current.booked_at = booked_iso
        current.value_date = value_iso
        current.counterparty_name = item.counterparty_name
        current.reference = item.reference
        current.currency = item.currency
        current.category = item.category or current.category or categorize(item.label)
        return True

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
        mark_sync_success(connection)
        self.engine.schedule_next_sync(connection)
        self.db.add(run)
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(run)
        metrics_registry.incr(
            "elfis_banking_sync_success_total",
            labels={"provider": connection.provider, "trigger": run.trigger},
        )
        if run.duration_ms is not None:
            metrics_registry.observe(
                "elfis_banking_sync_duration_ms",
                float(run.duration_ms),
                labels={"provider": connection.provider},
            )
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
                "organization_id": connection.organization_id,
                "connection_id": connection.id,
                "provider": connection.provider,
                "trigger": run.trigger,
                "transactions_created": run.transactions_created,
                "transactions_updated": run.transactions_updated,
                "duplicates_skipped": run.duplicates_skipped,
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
        error_code, _retryable = classify_connector_error(error)
        public_message = public_sync_error_message(error_code)
        run.status = SyncRunStatus.failed.value
        run.finished_at = datetime.utcnow()
        run.duration_ms = round((time.monotonic() - started) * 1000, 2)
        run.error_message = message[:500]
        connection.status = ConnectionStatus.error.value
        mark_sync_failed(connection, error_code=error_code, public_message=public_message)
        self.db.add(run)
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(run)
        metrics_registry.incr(
            "elfis_banking_sync_failed_total",
            labels={"provider": connection.provider, "error_code": error_code},
        )
        publish_sync_failed(
            self.db,
            organization_id=run.organization_id,
            run_id=run.id,
            connection_id=connection.id,
            provider=connection.provider,
            error_message=public_message,
            correlation_id=run.correlation_id,
        )
        logger.error(
            "banking_sync_failed",
            extra={
                "run_id": run.id,
                "organization_id": connection.organization_id,
                "connection_id": connection.id,
                "provider": connection.provider,
                "trigger": run.trigger,
                "attempts": run.attempt_count,
                "error_code": error_code,
                "duration_ms": run.duration_ms,
                "consecutive_sync_failures": connection.consecutive_sync_failures,
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
