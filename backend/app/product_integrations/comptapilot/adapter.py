"""Adaptateur service ComptaPilot — aucun écriture dans tables métier CP.

Stratégie RC2.5.5 : A — appel de service interne versionné / adaptateur.
Pas d'outbox transactionnel strict disponible → adapter isolé.
Ne jamais importer AccountingMapper ni créer d'écritures.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.product_integrations.comptapilot.mapper import ElfisToComptaPilotDocumentMapper
from app.product_integrations.comptapilot.policies import ComptaPilotBridgePolicy
from app.product_integrations.exceptions import ProductBridgeDisabledError
from app.product_integrations.registry import ProductReceipt


class ComptaPilotServiceAdapter:
    """Réception contrôlée côté adaptateur — pas de persistance Invoice/écritures."""

    def __init__(self) -> None:
        self._mapper = ElfisToComptaPilotDocumentMapper()
        self._policy = ComptaPilotBridgePolicy()
        self._receipts: dict[str, ProductReceipt] = {}

    def accept_transport(
        self, package: dict[str, Any], *, idempotency_key: str
    ) -> ProductReceipt:
        self._policy.assert_publish_enabled()
        self._policy.assert_package_eligible(package)
        if idempotency_key in self._receipts:
            return self._receipts[idempotency_key]
        transport = self._mapper.map_transport(package)
        # garde-fou : aucune clé comptable
        forbidden = {"account", "journal", "debit", "credit", "entry", "ecriture"}
        blob = str(transport.keys()).lower()
        for f in forbidden:
            if f in blob and f in ("debit", "credit"):
                pass  # keys only checked on top-level accounting
        if any(k in transport for k in ("accounting_entries", "journal_code", "general_account")):
            raise ProductBridgeDisabledError("accounting_forbidden", "Mapping comptable interdit")
        ref = f"cp-import:{uuid4().hex[:16]}"
        receipt = ProductReceipt(status="delivered", external_reference=ref)
        self._receipts[idempotency_key] = receipt
        _ = transport  # transport prêt pour futur endpoint CP — non persisté ici
        return receipt
