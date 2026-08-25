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
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.banking.account_types import normalize_account_type
from app.banking.banking_models import ElfisBankConnection, ElfisBankSyncRun
from app.banking.connectors import registry
from app.banking.connectors.base import ConnectorError
from app.banking.demo_gate import DEMO_PROVIDER, FICTIONAL_BANK_LABEL
from app.banking.engine import BankingEngine, BankingEngineError
from app.banking.iban import iban_last4, mask_iban
from app.models import BankAccount
from app.banking.health import BankingHealthService
from app.banking.sync_engine import SyncEngine
from app.config import settings
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription, require_platform_admin

router = APIRouter(
    prefix="/banking",
    tags=["banking"],
    dependencies=[Depends(require_active_subscription)],
)

callback_router = APIRouter(
    prefix="/banking/connectors/bridge",
    tags=["banking-bridge-callback"],
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
    iban_masked: str
    iban_last4: str | None
    account_type: str
    currency: str
    balance: float
    available_balance: float | None
    connected: bool
    last_sync_at: datetime | None
    balance_updated_at: datetime | None = None


def serialize_account(account: BankAccount) -> AccountOut:
    return AccountOut(
        id=account.id,
        connection_id=account.connection_id,
        provider=account.provider,
        external_id=account.external_id,
        label=account.label,
        bank_name=account.bank_name,
        iban_masked=mask_iban(account.iban),
        iban_last4=iban_last4(account.iban),
        account_type=normalize_account_type(getattr(account, "account_type", None)),
        currency=account.currency,
        balance=float(account.balance),
        available_balance=getattr(account, "available_balance", None),
        connected=account.connected,
        last_sync_at=account.last_sync_at,
        balance_updated_at=getattr(account, "balance_updated_at", None),
    )


class TransactionOut(BaseModel):
    id: int
    account_id: int
    external_id: str
    booked_at: str
    value_date: str | None = None
    label: str
    amount: float
    currency: str
    category: str
    status: str
    source: str
    counterparty_name: str | None = None
    reference: str | None = None
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
    from app.banking.engine import SyncAlreadyInProgressError

    if isinstance(exc, SyncAlreadyInProgressError):
        raise HTTPException(409, detail=str(exc)) from exc
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
    org_id = auth.require_organization_id()
    try:
        connector = registry.get_connector(payload.provider)
        if connector.requires_user_consent:
            connection, redirect_url = engine.begin_bank_consent(
                organization_id=org_id,
                provider=payload.provider,
                bank_name=payload.bank_name,
            )
            return {
                "ok": True,
                "redirect_url": redirect_url,
                "connection": ConnectionOut.model_validate(connection),
                "accounts": [],
                "message": "Redirection vers le consentement bancaire.",
            }
        connection = engine.connect(
            organization_id=org_id,
            provider=payload.provider,
            bank_name=payload.bank_name,
        )
    except (ConnectorError, BankingEngineError) as exc:
        _raise_domain(exc)
    message = f"Banque connectée via {connection.provider}."
    if connection.provider == DEMO_PROVIDER:
        message = f"{FICTIONAL_BANK_LABEL}. Aucune banque réelle n’a été connectée."
    return {
        "ok": True,
        "connection": ConnectionOut.model_validate(connection),
        "accounts": [
            serialize_account(a) for a in engine.accounts_for_connection(connection)
        ],
        "message": message,
    }


def _banking_frontend_redirect(result: str) -> RedirectResponse:
    base = (settings.frontend_url or "http://localhost:5173").rstrip("/")
    safe = result if result in {"ok", "denied", "error"} else "error"
    return RedirectResponse(f"{base}/platform/banking?consent={safe}", status_code=303)


@callback_router.get("/callback")
def bridge_connect_callback(
    db: Session = Depends(get_db),
    state: str | None = Query(default=None),
    context: str | None = Query(default=None),
    item_id: str | None = Query(default=None),
    success: str | None = Query(default=None),
    user_uuid: str | None = Query(default=None),
    step: str | None = Query(default=None),
    source: str | None = Query(default=None),
):
    """Retour Bridge Connect — pas d'auth navigateur ; le state HMAC lie org + tentative."""
    del user_uuid, step, source
    result = BankingEngine(db).finalize_bank_consent(
        state=state,
        context=context,
        item_id=item_id,
        success=success,
    )
    return _banking_frontend_redirect(result)


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
        "items": [serialize_account(a) for a in accounts],
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
