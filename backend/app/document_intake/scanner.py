"""Scanner architecture — stub antivirus (aucune analyse réelle Sprint 2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ScanVerdict(str, Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ScanResult:
    verdict: str
    engine: str
    details: dict


class IntakeScanner:
    """Point d'extension futur (ClamAV, etc.). V1 : toujours clean sauf flag forcé."""

    def scan(self, *, filename: str, head: bytes, size_bytes: int) -> ScanResult:
        # Architecture only — aucun antivirus réel
        return ScanResult(
            verdict=ScanVerdict.CLEAN.value,
            engine="noop_v1",
            details={"scanned": False, "reason": "scanner_stub"},
        )
