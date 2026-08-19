"""Endpoints Banking Platform V1.

/banking/connectors     — fournisseurs disponibles + connexions de l'organisation
/banking/accounts       — comptes (source de vérité Banking Engine)
/banking/transactions   — transactions normalisées (filtres + pagination)
/banking/sync           — déclenchement + journal des synchronisations
/banking/status         — statut global de l'organisation
/banking/health         — santé des connexions et des fournisseurs

/platform/banking/overview — Cockpit Admin (toutes organisations)
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.banking.banking_models import ElfisBankConnection, ElfisBankSyncRun
from app.banking.connectors.base import ConnectorError
from app.banking.engine import BankingEngine, BankingEngineError
from app.banking.health import BankingHealthService
from app.banking.sync_engine import SyncEngine
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription, require_platform_admin

router = APIRouter(
    prefix="/banking",
    tags=["banking"],
    dependencies=[Depends(require_active_subscription)],
)

admin_router = APIRouter(
    prefix="/platform/banking",
    tags=["platform-banking"],
    dependencies=[Depends(require_platform_admin)],
)


# --------------------------------------------------------------------- #
# Schémas
# --------------------------------------------------------------------- #


class ConnectionOut(BaseModel):
    id: int
    provider: str
    bank_name: str
    status: str
    error_message: str | None
    last_sync_at: datetime | None
    next_sync_at: datetime | None
    sync_interval_minutes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountOut(BaseModel):
    id: int
    connection_id: int | None
    provider: str
    external_id: str
    label: str
    bank_name: str
    iban: str
    currency: str
    balance: float
    connected: bool
    last_sync_at: datetime | None

    model_config = {"from_attributes": True}


class TransactionOut(BaseModel):
    id: int
    account_id: int
    external_id: str
    booked_at: str
    label: str
    amount: float
    currency: str
    category: str
    status: str
    source: str
    is_duplicate: bool
    is_anomaly: bool
    reconciled: bool

    model_config = {"from_attributes": True}


class SyncRunOut(BaseModel):
    id: str
    connection_id: int
    provider: str
    sync_type: str
    trigger: str
    status: str
    accounts_synced: int
    transactions_created: int
    transactions_updated: int
    duplicates_skipped: int
    attempt_count: int
    max_attempts: int
    cursor: str | None
    resumed_from_cursor: bool
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None
    duration_ms: float | None

    model_config = {"from_attributes": True}


class ConnectIn(BaseModel):
    provider: str = Field(min_length=2, max_length=32)
    bank_name: str = Field(default="", max_length=255)


class SyncIn(BaseModel):
    connection_id: int | None = None


def _raise_domain(exc: Exception) -> None:
    raise HTTPException(400, detail=str(exc)) from exc


# --------------------------------------------------------------------- #
# Connecteurs et connexions
# --------------------------------------------------------------------- #


@router.get("/connectors")
def list_connectors(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("bank.read")
    engine = BankingEngine(db)
    org_id = auth.require_organization_id()
    return {
        "providers": engine.available_connectors(),
        "connections": [
            ConnectionOut.model_validate(c) for c in engine.list_connections(org_id)
        ],
    }


@router.post("/connectors/connect")
def connect_bank(
    payload: ConnectIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("bank.connect")
    engine = BankingEngine(db)
    try:
        connection = engine.connect(
            organization_id=auth.require_organization_id(),
            provider=payload.provider,
            bank_name=payload.bank_name,
        )
    except (ConnectorError, BankingEngineError) as exc:
        _raise_domain(exc)
    return {
        "ok": True,
        "connection": ConnectionOut.model_validate(connection),
        "accounts": [
            AccountOut.model_validate(a) for a in engine.accounts_for_connection(connection)
        ],
        "message": f"Banque connectée via {connection.provider}.",
    }


@router.post("/connectors/{connection_id}/disconnect")
def disconnect_bank(
    connection_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("bank.connect")
    try:
        connection = BankingEngine(db).disconnect(
            organization_id=auth.require_organization_id(),
            connection_id=connection_id,
        )
    except BankingEngineError as exc:
        _raise_domain(exc)
    return {
        "ok": True,
        "connection": ConnectionOut.model_validate(connection),
        "message": "Banque déconnectée.",
    }


# --------------------------------------------------------------------- #
# Comptes et transactions
# --------------------------------------------------------------------- #


@router.get("/accounts")
def list_accounts(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("bank.read")
    accounts = BankingEngine(db).list_accounts(auth.require_organization_id())
    return {
        "items": [AccountOut.model_validate(a) for a in accounts],
        "total": len(accounts),
    }


@router.get("/transactions")
def list_transactions(
    account_id: int | None = Query(default=None),
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("bank.read")
    rows, total = BankingEngine(db).list_transactions(
        auth.require_organization_id(),
        account_id=account_id,
        category=category,
        status=status,
        source=source,
        search=q,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [TransactionOut.model_validate(t) for t in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# --------------------------------------------------------------------- #
# Synchronisation
# --------------------------------------------------------------------- #


@router.post("/sync")
def trigger_sync(
    payload: SyncIn | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("bank.connect")
    try:
        runs = SyncEngine(db).run_sync(
            auth.require_organization_id(),
            connection_id=payload.connection_id if payload else None,
            trigger="manual",
        )
    except BankingEngineError as exc:
        _raise_domain(exc)
    return {
        "ok": all(r.status == "completed" for r in runs),
        "runs": [SyncRunOut.model_validate(r) for r in runs],
    }


@router.get("/sync")
def list_sync_runs(
    connection_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("bank.read")
    runs = SyncEngine(db).list_runs(
        auth.require_organization_id(), connection_id=connection_id, limit=limit
    )
    return {"items": [SyncRunOut.model_validate(r) for r in runs], "total": len(runs)}


# --------------------------------------------------------------------- #
# Statut et santé
# --------------------------------------------------------------------- #


@router.get("/status")
def banking_status(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("bank.read")
    return BankingEngine(db).status(auth.require_organization_id())


@router.get("/health")
def banking_health(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("bank.read")
    return BankingHealthService(db).organization_health(auth.require_organization_id())


# --------------------------------------------------------------------- #
# Cockpit Admin (plateforme)
# --------------------------------------------------------------------- #


@admin_router.get("/overview")
def platform_banking_overview(db: Session = Depends(get_db)):
    return BankingHealthService(db).platform_overview()
