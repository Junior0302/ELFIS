"""Calcul de checksum pour ELFIS Vault."""

from __future__ import annotations

import hashlib


def calculate_sha256(content: bytes) -> str:
    """Retourne le digest SHA-256 hexadécimal du contenu binaire."""
    return hashlib.sha256(content).hexdigest()
