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
    NormalizedAccount,
    NormalizedTransaction,
)


class ConnectorError(Exception):
    """Erreur d'un fournisseur. ``retryable=True`` déclenche le retry du Sync Engine."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


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

    @abstractmethod
    def connect(self, *, organization_id: int, bank_name: str, options: dict | None = None) -> str:
        """Établit la connexion et retourne l'identifiant de connexion côté fournisseur."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self, provider_connection_id: str) -> None:
        """Révoque la connexion côté fournisseur."""
        raise NotImplementedError

    @abstractmethod
    def refresh(self, provider_connection_id: str) -> None:
        """Rafraîchit la session/consentement côté fournisseur."""
        raise NotImplementedError

    @abstractmethod
    def list_accounts(self, provider_connection_id: str) -> list[NormalizedAccount]:
        """Comptes normalisés de la connexion."""
        raise NotImplementedError

    @abstractmethod
    def list_transactions(
        self,
        provider_connection_id: str,
        account_external_id: str,
        *,
        since: date | None = None,
    ) -> list[NormalizedTransaction]:
        """Transactions normalisées ; ``since`` permet la synchronisation incrémentale."""
        raise NotImplementedError

    @abstractmethod
    def health(self) -> ConnectorHealth:
        """État du fournisseur (configuration, disponibilité)."""
        raise NotImplementedError
