"""Interface commune des connecteurs bancaires.

Tout fournisseur (Bridge, Powens, démo…) implémente ``BankConnector``.
Le reste de la plateforme ne connaît que cette interface et les types
normalisés de ``banking_types`` : les fournisseurs sont interchangeables.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import ClassVar

from app.banking.banking_types import (
    ConnectorHealth,
    ConsentCompleteResult,
    ConsentStartResult,
    NormalizedAccount,
    NormalizedTransaction,
    TransactionPage,
)


class ConnectorError(Exception):
    """Erreur d'un fournisseur. ``retryable=True`` déclenche le retry du Sync Engine."""

    def __init__(self, message: str, *, retryable: bool = False, status_code: int | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


class ConnectorNotConfiguredError(ConnectorError):
    """Le fournisseur n'a pas ses identifiants configurés."""

    def __init__(self, provider: str):
        super().__init__(
            f"Fournisseur '{provider}' non configuré (identifiants API manquants).",
            retryable=False,
        )


class BankConnector(ABC):
    """Contrat unique de la Banking Integration Layer."""

    provider: ClassVar[str] = ""
    display_name: ClassVar[str] = ""
    requires_user_consent: ClassVar[bool] = False

    def start_user_consent(
        self,
        *,
        organization_id: int,
        callback_url: str,
        bank_name: str = "",
        context: str = "",
    ) -> ConsentStartResult:
        raise ConnectorError("Ce fournisseur ne nécessite pas de consentement redirigé.")

    def complete_user_consent(
        self,
        *,
        organization_id: int,
        provider_item_id: str,
    ) -> ConsentCompleteResult:
        raise ConnectorError("Ce fournisseur ne nécessite pas de consentement redirigé.")

    @abstractmethod
    def connect(self, *, organization_id: int, bank_name: str, options: dict | None = None) -> str:
        """Établit la connexion et retourne l'identifiant de connexion côté fournisseur."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self, provider_connection_id: str, *, organization_id: int | None = None) -> None:
        """Révoque la connexion côté fournisseur."""
        raise NotImplementedError

    @abstractmethod
    def refresh(self, provider_connection_id: str, *, organization_id: int | None = None) -> None:
        """Rafraîchit la session/consentement côté fournisseur."""
        raise NotImplementedError

    @abstractmethod
    def list_accounts(
        self, provider_connection_id: str, *, organization_id: int | None = None
    ) -> list[NormalizedAccount]:
        """Comptes normalisés de la connexion."""
        raise NotImplementedError

    @abstractmethod
    def list_transactions(
        self,
        provider_connection_id: str,
        account_external_id: str,
        *,
        since: date | None = None,
        organization_id: int | None = None,
    ) -> list[NormalizedTransaction]:
        """Transactions normalisées ; ``since`` permet la synchronisation incrémentale."""
        raise NotImplementedError

    def list_transaction_page(
        self,
        provider_connection_id: str,
        account_external_id: str,
        *,
        since: date | None = None,
        cursor: str | None = None,
        organization_id: int | None = None,
    ) -> TransactionPage:
        """Page fournisseur. Défaut : une seule page via ``list_transactions``."""
        if cursor:
            raise ConnectorError(
                "Ce fournisseur ne pagine pas : curseur inattendu.",
                retryable=False,
            )
        return TransactionPage(
            transactions=self.list_transactions(
                provider_connection_id,
                account_external_id,
                since=since,
                organization_id=organization_id,
            ),
            next_cursor=None,
            has_more=False,
        )

    @abstractmethod
    def health(self) -> ConnectorHealth:
        """État du fournisseur (configuration, disponibilité)."""
        raise NotImplementedError
