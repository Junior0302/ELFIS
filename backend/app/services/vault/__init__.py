"""Package services ELFIS Vault."""

from app.services.vault.checksum_service import calculate_sha256
from app.services.vault.exceptions import (
    VaultAccessDeniedError,
    VaultDatabaseError,
    VaultDuplicateDocumentError,
    VaultFileTooLargeError,
    VaultInvalidFileError,
    VaultStorageError,
)

__all__ = [
    "archive_document",
    "calculate_sha256",
    "VaultAccessDeniedError",
    "VaultDatabaseError",
    "VaultDuplicateDocumentError",
    "VaultFileTooLargeError",
    "VaultInvalidFileError",
    "VaultStorageError",
]


def __getattr__(name: str):
    if name == "archive_document":
        from app.services.vault.vault_service import archive_document

        return archive_document
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
