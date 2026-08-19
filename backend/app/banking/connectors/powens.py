"""Connecteur Powens (ex-Budget Insight) — implémente l'interface commune.

Seul ce module connaît l'API Powens. Sans configuration
(``BANKING_POWENS_API_URL`` / ``BANKING_POWENS_CLIENT_ID`` / ``SECRET``),
le connecteur se déclare ``not_configured`` et refuse la connexion.
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


class PowensBankConnector(BankConnector):
    provider: ClassVar[str] = "powens"
    display_name: ClassVar[str] = "Powens"

    def __init__(self) -> None:
        self._base_url = (settings.banking_powens_api_url or "").rstrip("/")
        self._client_id = settings.banking_powens_client_id or ""
        self._client_secret = settings.banking_powens_client_secret or ""

    @property
    def configured(self) -> bool:
        return bool(self._base_url and self._client_id and self._client_secret)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        if not self.configured:
            raise ConnectorNotConfiguredError(self.provider)
        headers = {"Authorization": f"Bearer {self._client_secret}"}
        try:
            response = httpx.request(
                method,
                f"{self._base_url}{path}",
                headers=headers,
                timeout=20.0,
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise ConnectorError(f"Powens injoignable: {exc}", retryable=True) from exc
        if response.status_code >= 500:
            raise ConnectorError(
                f"Erreur Powens {response.status_code}", retryable=True
            )
        if response.status_code >= 400:
            raise ConnectorError(
                f"Requête Powens refusée ({response.status_code})", retryable=False
            )
        return response.json() if response.content else {}

    def connect(self, *, organization_id: int, bank_name: str, options: dict | None = None) -> str:
        data = self._request(
            "POST",
            "/2.0/auth/init",
            json={"client_id": self._client_id, "client_secret": self._client_secret},
        )
        connection_id = str(data.get("id_user") or data.get("id") or "")
        if not connection_id:
            raise ConnectorError("Powens n'a pas retourné d'identifiant de connexion.")
        return connection_id

    def disconnect(self, provider_connection_id: str) -> None:
        self._request("DELETE", f"/2.0/users/{provider_connection_id}/connections")

    def refresh(self, provider_connection_id: str) -> None:
        self._request("PUT", f"/2.0/users/{provider_connection_id}/connections")

    def list_accounts(self, provider_connection_id: str) -> list[NormalizedAccount]:
        data = self._request("GET", f"/2.0/users/{provider_connection_id}/accounts")
        accounts: list[NormalizedAccount] = []
        for raw in data.get("accounts", []):
            accounts.append(
                NormalizedAccount(
                    external_id=str(raw.get("id")),
                    label=str(raw.get("name") or "Compte"),
                    bank_name=str(raw.get("bank_name") or self.display_name),
                    iban=str(raw.get("iban") or ""),
                    currency=str((raw.get("currency") or {}).get("id") or "EUR"),
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
        params: dict[str, Any] = {"limit": 500}
        if since:
            params["min_date"] = since.isoformat()
        data = self._request(
            "GET",
            f"/2.0/users/{provider_connection_id}/accounts/{account_external_id}/transactions",
            params=params,
        )
        transactions: list[NormalizedTransaction] = []
        for raw in data.get("transactions", []):
            booked_raw = str(raw.get("date") or raw.get("rdate") or "")
            try:
                booked = datetime.strptime(booked_raw[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
            transactions.append(
                NormalizedTransaction(
                    external_id=str(raw.get("id")),
                    booked_at=booked,
                    label=str(raw.get("simplified_wording") or raw.get("wording") or "Opération"),
                    amount=float(raw.get("value") or 0.0),
                    currency=str((raw.get("currency") or {}).get("id") or "EUR"),
                    account_external_id=account_external_id,
                    status=(
                        TransactionStatus.pending
                        if raw.get("coming")
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
                message="Identifiants Powens absents (BANKING_POWENS_CLIENT_ID / SECRET).",
            )
        started = time.monotonic()
        try:
            self._request("GET", "/2.0/banks", params={"limit": 1})
            latency = int((time.monotonic() - started) * 1000)
            return ConnectorHealth(
                provider=self.provider,
                configured=True,
                status="ok",
                message="API Powens accessible.",
                latency_ms=latency,
            )
        except ConnectorError as exc:
            return ConnectorHealth(
                provider=self.provider,
                configured=True,
                status="unavailable",
                message=str(exc),
            )
