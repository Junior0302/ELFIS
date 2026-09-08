"""Scanner Document Intake — délègue au client antivirus partagé (clamd INSTREAM)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.security.antivirus import (
    AntivirusError,
    AntivirusVerdict,
    scan_user_upload,
)


class ScanVerdict(str, Enum):
    CLEAN = "clean"
    INFECTED = "infected"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    ERROR = "error"
    SUSPICIOUS = "suspicious"


@dataclass(frozen=True)
class ScanResult:
    verdict: str
    engine: str
    details: dict
    signature: str | None = None
    scanned: bool = False


class IntakeScanner:
    """Scan complet du fichier. Jamais de ready_for_analysis si verdict != clean."""

    def scan(self, *, filename: str, content: bytes, size_bytes: int) -> ScanResult:
        # filename n'est jamais loggé ni envoyé à clamd comme métadonnée métier.
        result = scan_user_upload(data=content, upload_type="document_intake")
        verdict = result.verdict.value
        if result.verdict == AntivirusVerdict.ERROR:
            verdict = ScanVerdict.ERROR.value
        return ScanResult(
            verdict=verdict,
            engine=result.engine,
            signature=result.signature,
            scanned=result.scanned,
            details=dict(result.details or {}),
        )

    def require_clean(self, *, filename: str, content: bytes, size_bytes: int) -> ScanResult:
        scan = self.scan(filename=filename, content=content, size_bytes=size_bytes)
        if scan.verdict != ScanVerdict.CLEAN.value:
            if scan.verdict == ScanVerdict.INFECTED.value:
                raise AntivirusError("file_infected")
            if scan.verdict == ScanVerdict.UNAVAILABLE.value:
                raise AntivirusError("antivirus_unavailable")
            raise AntivirusError("file_scan_failed")
        return scan
