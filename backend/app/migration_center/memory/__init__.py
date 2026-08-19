"""Migration Memory — interface extensible (pas d'apprentissage IA réel)."""

from __future__ import annotations

from .enums import MemoryScope, MemorySource, MemoryStatus, MemoryType
from .service import MigrationMemoryService

__all__ = [
    "MigrationMemoryService",
    "MemoryScope",
    "MemorySource",
    "MemoryStatus",
    "MemoryType",
]
