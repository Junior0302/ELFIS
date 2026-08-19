"""Connecteur de démonstration — fonctionne hors ligne, données déterministes.

Sert de fournisseur par défaut en local et de référence d'implémentation.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import ClassVar

from app.banking.banking_types import (
    ConnectorHealth,
    NormalizedAccount,
    NormalizedTransaction,
    TransactionStatus,
)
from app.banking.connectors.base import BankConnector, ConnectorError

_DEMO_OPERATIONS: list[tuple[int, str, float]] = [
    # (jours avant aujourd'hui, libellé, montant)
    (28, "VIREMENT CLIENT DUPONT SARL", 2400.0),
    (26, "LOYER BUREAUX PARIS", -1450.0),
    (24, "GOOGLE ADS CAMPAGNE", -320.5),
    (21, "SALAIRE ASSISTANTE", -1980.0),
    (18, "ENCAISSEMENT STRIPE", 890.75),
    (14, "EDF ELECTRICITE", -142.3),
    (10, "VIREMENT CLIENT MARTIN & CO", 1750.0),
    (7, "ABONNEMENT NOTION", -12.0),
    (4, "COMMISSION FRAIS BANCAIRES", -8.9),
    (1, "ENCAISSEMENT PAYPAL", 310.4),
]


class DemoBankConnector(BankConnector):
    provider: ClassVar[str] = "demo"
    display_name: ClassVar[str] = "Banque Démo ELFIS"

    def connect(self, *, organization_id: int, bank_name: str, options: dict | None = None) -> str:
        return f"demo-conn-{organization_id}"

    def disconnect(self, provider_connection_id: str) -> None:
        return None

    def refresh(self, provider_connection_id: str) -> None:
        return None

    def list_accounts(self, provider_connection_id: str) -> list[NormalizedAccount]:
        if not provider_connection_id.startswith("demo-conn-"):
            raise ConnectorError("Connexion démo inconnue.", retryable=False)
        balance = round(sum(amount for _, _, amount in _DEMO_OPERATIONS) + 12000.0, 2)
        return [
            NormalizedAccount(
                external_id=f"{provider_connection_id}-acc-1",
                label="Compte courant pro",
                bank_name=self.display_name,
                iban="FR7630001007941234567890185",
                currency="EUR",
                balance=balance,
            )
        ]

    def list_transactions(
        self,
        provider_connection_id: str,
        account_external_id: str,
        *,
        since: date | None = None,
    ) -> list[NormalizedTransaction]:
        today = date.today()
        out: list[NormalizedTransaction] = []
        for days_ago, label, amount in _DEMO_OPERATIONS:
            booked = today - timedelta(days=days_ago)
            if since and booked <= since:
                continue
            fingerprint = f"{account_external_id}|{booked.isoformat()}|{label}|{amount:.2f}"
            external_id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:32]
            out.append(
                NormalizedTransaction(
                    external_id=external_id,
                    booked_at=booked,
                    label=label,
                    amount=amount,
                    currency="EUR",
                    account_external_id=account_external_id,
                    status=TransactionStatus.booked,
                    source=self.provider,
                )
            )
        return out

    def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            provider=self.provider,
            configured=True,
            status="ok",
            message="Connecteur démo local — toujours disponible.",
            latency_ms=1,
        )
