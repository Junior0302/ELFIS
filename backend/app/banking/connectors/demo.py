"""Connecteur de démonstration — fonctionne hors ligne, données déterministes.

Sert de fournisseur par défaut en local et de référence d'implémentation.
BANK-3 : pagination, deux mouvements identiques, pending → booked (même ID).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import ClassVar

from app.banking.banking_types import (
    ConnectorHealth,
    NormalizedAccount,
    NormalizedTransaction,
    TransactionPage,
    TransactionStatus,
)
from app.banking.connectors.base import BankConnector, ConnectorError

_DEMO_PAGE_SIZE = 5

# (jours avant aujourd'hui, libellé, montant, id stable, pending_until_incremental)
_DEMO_OPERATIONS: list[tuple[int, str, float, str, bool]] = [
    (28, "VIREMENT CLIENT DUPONT SARL", 2400.0, "demo-tx-01", False),
    (26, "LOYER BUREAUX PARIS", -1450.0, "demo-tx-02", False),
    (24, "GOOGLE ADS CAMPAGNE", -320.5, "demo-tx-03", False),
    (21, "SALAIRE ASSISTANTE", -1980.0, "demo-tx-04", False),
    (18, "ENCAISSEMENT STRIPE", 890.75, "demo-tx-05", False),
    (14, "EDF ELECTRICITE", -142.3, "demo-tx-06", False),
    (10, "VIREMENT CLIENT MARTIN & CO", 1750.0, "demo-tx-07", False),
    (7, "ABONNEMENT NOTION", -12.0, "demo-tx-08", False),
    (4, "COMMISSION FRAIS BANCAIRES", -8.9, "demo-tx-09", False),
    (3, "RESTAURANT", -25.0, "demo-tx-rest-a", False),
    (3, "RESTAURANT", -25.0, "demo-tx-rest-b", False),
    (1, "ENCAISSEMENT PAYPAL", 310.4, "demo-tx-10", False),
    (0, "PAIEMENT CARTE EN ATTENTE", -40.0, "demo-tx-card-pending", True),
]


def _demo_rows(
    account_external_id: str, *, since: date | None, incremental: bool
) -> list[NormalizedTransaction]:
    today = date.today()
    out: list[NormalizedTransaction] = []
    for days_ago, label, amount, external_id, pending_first in _DEMO_OPERATIONS:
        booked = today - timedelta(days=days_ago)
        if since and booked <= since:
            continue
        status = TransactionStatus.booked
        if pending_first and not incremental:
            status = TransactionStatus.pending
        out.append(
            NormalizedTransaction(
                external_id=external_id,
                booked_at=booked,
                value_date=booked,
                label=label,
                amount=amount,
                currency="EUR",
                account_external_id=account_external_id,
                status=status,
                source="demo",
                counterparty_name=label.split()[0] if label else None,
                reference=external_id.replace("demo-tx-", "REF-"),
            )
        )
    return out


def _page_index(cursor: str | None) -> int:
    if not cursor:
        return 0
    if not cursor.startswith("p:"):
        raise ConnectorError("Curseur de pagination démo invalide.", retryable=False)
    try:
        return int(cursor.split(":", 1)[1])
    except (TypeError, ValueError) as exc:
        raise ConnectorError("Curseur de pagination démo invalide.", retryable=False) from exc


class DemoBankConnector(BankConnector):
    provider: ClassVar[str] = "demo"
    display_name: ClassVar[str] = "Banque Démo ELFIS"

    def connect(self, *, organization_id: int, bank_name: str, options: dict | None = None) -> str:
        return f"demo-conn-{organization_id}"

    def disconnect(self, provider_connection_id: str, *, organization_id: int | None = None) -> None:
        return None

    def refresh(self, provider_connection_id: str, *, organization_id: int | None = None) -> None:
        return None

    def list_accounts(
        self, provider_connection_id: str, *, organization_id: int | None = None
    ) -> list[NormalizedAccount]:
        if not provider_connection_id.startswith("demo-conn-"):
            raise ConnectorError("Connexion démo inconnue.", retryable=False)
        balance = round(sum(amount for _, _, amount, _, _ in _DEMO_OPERATIONS) + 12000.0, 2)
        return [
            NormalizedAccount(
                external_id=f"{provider_connection_id}-acc-1",
                label="Compte courant pro",
                bank_name=self.display_name,
                iban="FR7630001007941234567890185",
                currency="EUR",
                balance=balance,
                available_balance=None,
                account_type="checking",
            )
        ]

    def list_transactions(
        self,
        provider_connection_id: str,
        account_external_id: str,
        *,
        since: date | None = None,
        organization_id: int | None = None,
    ) -> list[NormalizedTransaction]:
        return _demo_rows(account_external_id, since=since, incremental=since is not None)

    def list_transaction_page(
        self,
        provider_connection_id: str,
        account_external_id: str,
        *,
        since: date | None = None,
        cursor: str | None = None,
        organization_id: int | None = None,
    ) -> TransactionPage:
        rows = _demo_rows(account_external_id, since=since, incremental=since is not None)
        index = _page_index(cursor)
        start = index * _DEMO_PAGE_SIZE
        if index < 0 or (index > 0 and start >= len(rows) and rows):
            raise ConnectorError("Pagination démo incohérente.", retryable=False)
        chunk = rows[start : start + _DEMO_PAGE_SIZE]
        has_more = start + _DEMO_PAGE_SIZE < len(rows)
        return TransactionPage(
            transactions=chunk,
            next_cursor=f"p:{index + 1}" if has_more else None,
            has_more=has_more,
        )

    def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            provider=self.provider,
            configured=True,
            status="ok",
            message="Connecteur démo local — toujours disponible.",
            latency_ms=1,
        )
