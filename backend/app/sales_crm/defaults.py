"""SalesPilot CRM — default pipeline stages (configurable per org)."""

from __future__ import annotations

DEFAULT_PIPELINE_NAME = "Pipeline commercial"
DEFAULT_PIPELINE_CODE = "default"

# (code, name, position, probability, is_won, is_lost)
DEFAULT_STAGES: tuple[tuple[str, str, int, int, bool, bool], ...] = (
    ("prospection", "Prospection", 10, 10, False, False),
    ("qualification", "Qualification", 20, 20, False, False),
    ("decouverte", "Découverte", 30, 40, False, False),
    ("proposition", "Proposition", 40, 60, False, False),
    ("negociation", "Négociation", 50, 80, False, False),
    ("gagne", "Gagné", 90, 100, True, False),
    ("perdu", "Perdu", 100, 0, False, True),
)

DEFAULT_LOST_REASONS: tuple[tuple[str, str], ...] = (
    ("price", "Prix trop élevé"),
    ("competitor", "Concurrent retenu"),
    ("no_budget", "Pas de budget"),
    ("no_decision", "Pas de décision"),
    ("other", "Autre"),
)

DEFAULT_WIN_REASONS: tuple[tuple[str, str], ...] = (
    ("value", "Meilleure proposition de valeur"),
    ("relationship", "Relation / confiance"),
    ("price", "Prix compétitif"),
    ("product", "Produit adapté"),
    ("other", "Autre"),
)
