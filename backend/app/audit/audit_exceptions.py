"""Exceptions Audit Engine — jamais propagées vers le métier par défaut."""

from __future__ import annotations


class AuditError(Exception):
    """Erreur de base du moteur d'audit."""


class AuditValidationError(AuditError):
    """Données d'événement invalides (catégorie / severity / action)."""


class AuditPersistenceError(AuditError):
    """Échec d'écriture en base — journalisé, métier non interrompu."""


class AuditNotFoundError(AuditError):
    """Événement introuvable."""
