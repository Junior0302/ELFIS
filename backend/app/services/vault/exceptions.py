"""Exceptions métier ELFIS Vault."""

from __future__ import annotations


class VaultError(Exception):
    """Erreur de base Vault."""


class VaultAccessDeniedError(VaultError):
    """Utilisateur non autorisé à archiver pour cette entreprise."""


class VaultInvalidFileError(VaultError):
    """Fichier invalide (MIME, extension, signature)."""


class VaultFileTooLargeError(VaultError):
    """Fichier au-delà de la taille maximale autorisée."""

    def __init__(self, max_mb: int):
        self.max_mb = max_mb
        super().__init__(f"Fichier trop volumineux (max {max_mb} Mo)")


class VaultDuplicateDocumentError(VaultError):
    """Document déjà présent (même checksum pour le tenant)."""

    def __init__(self, existing_document_id: str):
        self.existing_document_id = existing_document_id
        super().__init__("Ce document est déjà présent dans ELFIS Vault.")


class VaultStorageError(VaultError):
    """Échec temporaire ou permanent du stockage objet."""


class VaultDatabaseError(VaultError):
    """Échec d'écriture / lecture base de données Vault."""
