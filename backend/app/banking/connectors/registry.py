"""Registre des connecteurs — point d'entrée unique vers les fournisseurs.

Le code métier (engine, sync, API) ne référence jamais un connecteur
directement : il demande une instance au registre par son nom.
"""

from __future__ import annotations

from typing import Callable

from app.banking.connectors.base import BankConnector, ConnectorError
from app.banking.connectors.bridge import BridgeBankConnector
from app.banking.connectors.demo import DemoBankConnector
from app.banking.connectors.powens import PowensBankConnector

_FACTORIES: dict[str, Callable[[], BankConnector]] = {}


def register_connector(provider: str, factory: Callable[[], BankConnector]) -> None:
    _FACTORIES[provider] = factory


def unregister_connector(provider: str) -> None:
    _FACTORIES.pop(provider, None)


def get_connector(provider: str) -> BankConnector:
    factory = _FACTORIES.get(provider)
    if factory is None:
        raise ConnectorError(f"Fournisseur inconnu: '{provider}'")
    return factory()


def list_providers() -> list[str]:
    return sorted(_FACTORIES.keys())


register_connector(DemoBankConnector.provider, DemoBankConnector)
register_connector(BridgeBankConnector.provider, BridgeBankConnector)
register_connector(PowensBankConnector.provider, PowensBankConnector)
