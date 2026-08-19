"""Connecteur Bridge (bridgeapi.io) — implémente l'interface commune.

Seul ce module connaît l'API Bridge. Sans identifiants configurés
(``BANKING_BRIDGE_CLIENT_ID`` / ``BANKING_BRIDGE_CLIENT_SECRET``), le
connecteur se déclare ``not_configured`` et refuse la connexion.
"""

from __future__ import annotations

import time
from datetime import date, datetime
from typing import Any, ClassVar

import httpx

from app.banking.banking_types import (
    ConnectorHealth,
    NormalizedAccount,
    NormalizedTransaction,
    TransactionStatus,
)
from app.banking.connectors.base import (
    BankConnector,
    ConnectorError,
    ConnectorNotConfiguredError,
)
from app.config import settings


class BridgeBankConnector(BankConnector):
    provider: ClassVar[str] = "bridge"
    display_name: ClassVar[str] = "Bridge"

    def __init__(self) -> None:
        self._base_url = (settings.banking_bridge_api_url or "").rstrip("/")
        self._client_id = settings.banking_bridge_client_id or ""
        self._client_secret = settings.banking_bridge_client_secret or ""

    @property
    def configured(self) -> bool:
        return bool(self._base_url and self._client_id and self._client_secret)

    def _headers(self) -> dict[str, str]:
        return {
            "Bridge-Version": "2025-01-15",
            "Client-Id": self._client_id,
            "Client-Secret": self._client_secret,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        if not self.configured:
            raise ConnectorNotConfiguredError(self.provider)
        try:
            response = httpx.request(
                method,
                f"{self._base_url}{path}",
                headers=self._headers(),
                timeout=20.0,
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise ConnectorError(f"Bridge injoignable: {exc}", retryable=True) from exc
        if response.status_code >= 500:
            raise ConnectorError(
                f"Erreur Bridge {response.status_code}", retryable=True
            )
        if response.status_code >= 400:
            raise ConnectorError(
                f"Requête Bridge refusée ({response.status_code})", retryable=False
            )
        return response.json() if response.content else {}

    def connect(self, *, organization_id: int, bank_name: str, options: dict | None = None) -> str:
        data = self._request(
            "POST",
            "/v3/aggregation/items",
            json={"external_user_id": f"elfis-org-{organization_id}"},
        )
        item_id = str(data.get("id") or "")
        if not item_id:
            raise ConnectorError("Bridge n'a pas retourné d'identifiant de connexion.")
        return item_id

    def disconnect(self, provider_connection_id: str) -> None:
        self._request("DELETE", f"/v3/aggregation/items/{provider_connection_id}")

    def refresh(self, provider_connection_id: str) -> None:
        self._request("POST", f"/v3/aggregation/items/{provider_connection_id}/refresh")

    def list_accounts(self, provider_connection_id: str) -> list[NormalizedAccount]:
        data = self._request(
            "GET", "/v3/aggregation/accounts", params={"item_id": provider_connection_id}
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
                )
            )
        return accounts

    def list_transactions(
        self,
        provider_connection_id: str,
        account_external_id: str,
        *,
        since: date | None = None,
    ) -> list[NormalizedTransaction]:
        params: dict[str, Any] = {"account_id": account_external_id, "limit": 500}
        if since:
            params["since"] = since.isoformat()
        data = self._request("GET", "/v3/aggregation/transactions", params=params)
        transactions: list[NormalizedTransaction] = []
        for raw in data.get("resources", []):
            booked_raw = str(raw.get("booking_date") or raw.get("date") or "")
            try:
                booked = datetime.strptime(booked_raw[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
            transactions.append(
                NormalizedTransaction(
                    external_id=str(raw.get("id")),
                    booked_at=booked,
                    label=str(raw.get("clean_description") or raw.get("provider_description") or "Opération"),
                    amount=float(raw.get("amount") or 0.0),
                    currency=str(raw.get("currency_code") or "EUR"),
                    account_external_id=account_external_id,
                    status=(
                        TransactionStatus.pending
                        if raw.get("future") or raw.get("status") == "pending"
                        else TransactionStatus.booked
                    ),
                    source=self.provider,
                )
            )
        return transactions

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
