"""Connecteur Bridge — API aggregation v3 (Bridge-Version 2025-01-15).

Seul ce module connaît l'API Bridge. BankingEngine et SyncEngine restent
indépendants du fournisseur.

Identifiants : BANKING_BRIDGE_CLIENT_ID / BANKING_BRIDGE_CLIENT_SECRET.
Aucun secret, token ou URL de session n'est journalisé.

BANK-5 : ``authentication_expires_at`` et ``status_code`` d'item sont lus
au callback / webhook puis persistés (dates + codes normalisés uniquement).
Jamais de token ni de payload brut.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Any, ClassVar

import httpx

from app.banking.account_types import normalize_account_type
from app.banking.banking_types import (
    ConnectorHealth,
    ConsentCompleteResult,
    ConsentStartResult,
    NormalizedAccount,
    NormalizedTransaction,
    TransactionPage,
    TransactionStatus,
    optional_provider_date,
    optional_provider_datetime,
    optional_provider_float,
)
from app.banking.transaction_identity import provider_transaction_id
from app.banking.connectors.base import (
    BankConnector,
    ConnectorError,
    ConnectorNotConfiguredError,
)
from app.config import settings

logger = logging.getLogger(__name__)

BRIDGE_API_VERSION = "2025-01-15"


def map_bridge_transaction(raw: dict[str, Any], account_external_id: str) -> NormalizedTransaction | None:
    """Mappe un objet Bridge connu — ignore les champs inconnus, jamais d'IBAN."""
    booked = optional_provider_date(raw.get("booking_date") or raw.get("date"))
    if booked is None:
        return None
    counterparty = raw.get("counterparty")
    name: str | None = None
    if isinstance(counterparty, dict):
        name = str(counterparty.get("name") or counterparty.get("label") or "") or None
    elif isinstance(counterparty, str):
        name = counterparty.strip() or None
    merchant = raw.get("merchant")
    if not name and isinstance(merchant, dict):
        name = str(merchant.get("name") or "") or None
    return NormalizedTransaction(
        external_id=provider_transaction_id(raw.get("id")),
        booked_at=booked,
        value_date=optional_provider_date(raw.get("value_date") or raw.get("transaction_date")),
        label=str(
            raw.get("clean_description") or raw.get("provider_description") or "Opération"
        ),
        amount=float(raw.get("amount") or 0.0),
        currency=str(raw.get("currency_code") or "EUR"),
        account_external_id=account_external_id,
        status=(
            TransactionStatus.pending
            if raw.get("future") or raw.get("status") == "pending"
            else TransactionStatus.booked
        ),
        source="bridge",
        counterparty_name=name,
        reference=str(raw.get("reference") or "").strip() or None,
    )


def _bridge_next_cursor(data: dict[str, Any]) -> str | None:
    pagination = data.get("pagination") if isinstance(data.get("pagination"), dict) else {}
    after = pagination.get("after") or pagination.get("next")
    if after:
        return str(after)
    next_uri = str(pagination.get("next_uri") or "")
    if "after=" in next_uri:
        return next_uri.split("after=", 1)[1].split("&", 1)[0] or None
    return None


def bridge_external_user_id(organization_id: int) -> str:
    """Identifiant Bridge déterministe — pas de persistance du user UUID."""
    return f"elfis-org-{int(organization_id)}"


class BridgeBankConnector(BankConnector):
    provider: ClassVar[str] = "bridge"
    display_name: ClassVar[str] = "Bridge"
    requires_user_consent: ClassVar[bool] = True

    def __init__(self) -> None:
        self._base_url = (settings.banking_bridge_api_url or "").rstrip("/")
        self._client_id = settings.banking_bridge_client_id or ""
        self._client_secret = settings.banking_bridge_client_secret or ""

    @property
    def configured(self) -> bool:
        return bool(self._base_url and self._client_id and self._client_secret)

    def _client_headers(self) -> dict[str, str]:
        return {
            "Bridge-Version": BRIDGE_API_VERSION,
            "Client-Id": self._client_id,
            "Client-Secret": self._client_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        access_token: str | None = None,
        **kwargs: Any,
    ) -> dict:
        if not self.configured:
            raise ConnectorNotConfiguredError(self.provider)
        headers = self._client_headers()
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        try:
            response = httpx.request(
                method,
                f"{self._base_url}{path}",
                headers=headers,
                timeout=20.0,
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise ConnectorError(f"Bridge injoignable: {exc}", retryable=True) from exc
        if response.status_code == 429:
            raise ConnectorError(
                f"Erreur Bridge {response.status_code}",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code >= 500:
            raise ConnectorError(
                f"Erreur Bridge {response.status_code}",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            item_status = None
            info = None
            try:
                body = response.json() if response.content else {}
            except ValueError:
                body = {}
            if isinstance(body, dict):
                raw_status = body.get("status_code")
                nested = body.get("error") if isinstance(body.get("error"), dict) else {}
                if raw_status is None:
                    raw_status = nested.get("status_code")
                try:
                    item_status = int(raw_status) if raw_status is not None else None
                except (TypeError, ValueError):
                    item_status = None
                info = str(body.get("status_code_info") or nested.get("code") or "")[:80] or None
            raise ConnectorError(
                f"Requête Bridge refusée ({response.status_code})",
                retryable=False,
                status_code=response.status_code,
                item_status_code=item_status,
                provider_code=info,
            )
        return response.json() if response.content else {}

    def _ensure_user(self, organization_id: int) -> None:
        external_id = bridge_external_user_id(organization_id)
        try:
            self._request(
                "POST",
                "/v3/aggregation/users",
                json={"external_user_id": external_id},
            )
        except ConnectorError as exc:
            if exc.status_code == 409:
                return
            raise

    def _access_token(self, organization_id: int) -> str:
        self._ensure_user(organization_id)
        data = self._request(
            "POST",
            "/v3/aggregation/authorization/token",
            json={"external_user_id": bridge_external_user_id(organization_id)},
        )
        token = str(data.get("access_token") or "").strip()
        if not token:
            raise ConnectorError("Bridge n'a pas retourné de jeton d'autorisation.")
        return token

    def start_user_consent(
        self,
        *,
        organization_id: int,
        callback_url: str,
        bank_name: str = "",
        context: str = "",
        provider_item_id: str = "",
        force_reauthentication: bool = False,
    ) -> ConsentStartResult:
        token = self._access_token(organization_id)
        payload: dict[str, Any] = {
            "user_email": f"org-{int(organization_id)}@banking.elfis.invalid",
            "callback_url": callback_url,
        }
        if context:
            payload["context"] = context
        item_id = str(provider_item_id or "").strip()
        if item_id:
            payload["item_id"] = int(item_id) if item_id.isdigit() else item_id
            if force_reauthentication:
                payload["force_reauthentication"] = True
        data = self._request(
            "POST",
            "/v3/aggregation/connect-sessions",
            access_token=token,
            json=payload,
        )
        url = str(data.get("url") or "").strip()
        if not url:
            raise ConnectorError("Bridge n'a pas retourné d'URL Connect.")
        logger.info(
            "banking_bridge_connect_session_created",
            extra={"organization_id": organization_id, "reauth": bool(item_id)},
        )
        return ConsentStartResult(redirect_url=url)

    def complete_user_consent(
        self,
        *,
        organization_id: int,
        provider_item_id: str,
    ) -> ConsentCompleteResult:
        item_id = str(provider_item_id or "").strip()
        if not item_id:
            raise ConnectorError("Identifiant d'item Bridge manquant.")
        token = self._access_token(organization_id)
        data = self._request(
            "GET",
            f"/v3/aggregation/items/{item_id}",
            access_token=token,
        )
        remote_id = str(data.get("id") or item_id)
        if remote_id != item_id:
            raise ConnectorError("Item Bridge incohérent avec la tentative de connexion.")
        expires = data.get("authentication_expires_at")
        expires_at = str(expires) if expires else None
        raw_status = data.get("status_code")
        try:
            status_code = int(raw_status) if raw_status is not None else None
        except (TypeError, ValueError):
            status_code = None
        info = str(data.get("status_code_info") or "")[:80] or None
        logger.info(
            "banking_bridge_item_validated",
            extra={"organization_id": organization_id, "item_present": True},
        )
        return ConsentCompleteResult(
            provider_connection_id=item_id,
            bank_name=str(data.get("provider_name") or self.display_name),
            authentication_expires_at=expires_at,
            status_code=status_code,
            status_code_info=info,
        )

    def connect(self, *, organization_id: int, bank_name: str, options: dict | None = None) -> str:
        raise ConnectorError(
            "Bridge nécessite un consentement utilisateur (Connect Session).",
            retryable=False,
        )

    def disconnect(self, provider_connection_id: str, *, organization_id: int | None = None) -> None:
        if not provider_connection_id or organization_id is None:
            return
        token = self._access_token(organization_id)
        self._request(
            "DELETE",
            f"/v3/aggregation/items/{provider_connection_id}",
            access_token=token,
        )

    def refresh(self, provider_connection_id: str, *, organization_id: int | None = None) -> None:
        if not provider_connection_id or organization_id is None:
            return
        token = self._access_token(organization_id)
        self._request(
            "POST",
            f"/v3/aggregation/items/{provider_connection_id}/refresh",
            access_token=token,
        )

    def list_accounts(
        self, provider_connection_id: str, *, organization_id: int | None = None
    ) -> list[NormalizedAccount]:
        if organization_id is None:
            raise ConnectorError("Organisation requise pour lire les comptes Bridge.")
        token = self._access_token(organization_id)
        data = self._request(
            "GET",
            "/v3/aggregation/accounts",
            access_token=token,
            params={"item_id": provider_connection_id},
        )
        accounts: list[NormalizedAccount] = []
        for raw in data.get("resources", []):
            accounts.append(
                NormalizedAccount(
                    external_id=str(raw.get("id")),
                    label=str(raw.get("name") or "Compte"),
                    bank_name=str(raw.get("provider_name") or self.display_name),
                    iban=str(raw.get("iban") or ""),
                    currency=str(raw.get("currency_code") or "EUR"),
                    balance=float(raw.get("balance") or 0.0),
                    available_balance=optional_provider_float(raw.get("available_balance")),
                    account_type=normalize_account_type(raw.get("type")),
                    balance_updated_at=optional_provider_datetime(
                        raw.get("updated_at") or raw.get("balance_updated_at")
                    ),
                )
            )
        return accounts

    def list_transactions(
        self,
        provider_connection_id: str,
        account_external_id: str,
        *,
        since: date | None = None,
        organization_id: int | None = None,
    ) -> list[NormalizedTransaction]:
        page = self.list_transaction_page(
            provider_connection_id,
            account_external_id,
            since=since,
            organization_id=organization_id,
        )
        return list(page.transactions)

    def list_transaction_page(
        self,
        provider_connection_id: str,
        account_external_id: str,
        *,
        since: date | None = None,
        cursor: str | None = None,
        organization_id: int | None = None,
    ) -> TransactionPage:
        if organization_id is None:
            raise ConnectorError("Organisation requise pour lire les transactions Bridge.")
        token = self._access_token(organization_id)
        params: dict[str, Any] = {"account_id": account_external_id, "limit": 200}
        if since:
            params["since"] = since.isoformat()
        if cursor:
            params["after"] = cursor
        data = self._request(
            "GET",
            "/v3/aggregation/transactions",
            access_token=token,
            params=params,
        )
        transactions = [
            mapped
            for raw in data.get("resources", [])
            if isinstance(raw, dict)
            for mapped in [map_bridge_transaction(raw, account_external_id)]
            if mapped is not None
        ]
        next_cursor = _bridge_next_cursor(data)
        return TransactionPage(
            transactions=transactions,
            next_cursor=next_cursor,
            has_more=bool(next_cursor),
        )

    def health(self) -> ConnectorHealth:
        if not self.configured:
            return ConnectorHealth(
                provider=self.provider,
                configured=False,
                status="not_configured",
                message="Identifiants Bridge absents (BANKING_BRIDGE_CLIENT_ID / SECRET).",
            )
        started = time.monotonic()
        try:
            self._request("GET", "/v3/providers", params={"limit": 1})
            latency = int((time.monotonic() - started) * 1000)
            return ConnectorHealth(
                provider=self.provider,
                configured=True,
                status="ok",
                message="API Bridge accessible.",
                latency_ms=latency,
            )
        except ConnectorError as exc:
            return ConnectorHealth(
                provider=self.provider,
                configured=True,
                status="unavailable",
                message=str(exc),
            )
