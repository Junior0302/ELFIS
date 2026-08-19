"""Enums Accounting Intelligence V2."""

from __future__ import annotations

from enum import Enum


class FeedbackAction(str, Enum):
    ACCEPT = "accept"
    MODIFY = "modify"
    REJECT = "reject"


class RecommendationSource(str, Enum):
    RULES = "rules"
    COMPANY = "company"
    HISTORY = "history"
    SIMILARITY = "similarity"
    AI = "ai"
    DEFAULTS = "defaults"


class LearningGate(str, Enum):
    """Motifs de refus d'apprentissage."""

    OK = "ok"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    INCOMPLETE = "incomplete"
    IMPORT_REJECTED = "import_rejected"
