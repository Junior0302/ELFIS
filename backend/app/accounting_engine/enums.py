"""Enums Accounting Engine V2."""

from __future__ import annotations

from enum import Enum


class ProposalV2Status(str, Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    REQUIRES_REVIEW = "requires_review"
    REGENERATED = "regenerated"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"


class DocumentDirection(str, Enum):
    PURCHASE = "purchase"  # achat
    SALE = "sale"  # vente
    BANK = "bank"
    CASH = "cash"
    OD = "od"
    CREDIT_NOTE = "credit_note"


class JournalCode(str, Enum):
    ACH = "ACH"  # Achats
    VTE = "VTE"  # Ventes
    BQ = "BQ"  # Banque
    CA = "CA"  # Caisse
    OD = "OD"  # Opérations diverses


class AccountPlan(str, Enum):
    PCG_FR = "pcg_fr"
    CUSTOM = "custom"


class LearningSource(str, Enum):
    USER_VALIDATION = "user_validation"
    MANUAL_OVERRIDE = "manual_override"


STANDARD_VAT_RATES = (0.0, 5.5, 10.0, 20.0)
