"""Provider noop — aucun OCR / IA / lecture de contenu."""

from __future__ import annotations


class NoopProcessingProvider:
    """Placeholder pour futurs providers métier (OCR, classification, etc.)."""

    name = "noop"

    async def process(self, *, document_id: str, version_id: str) -> dict:
        return {
            "provider": self.name,
            "document_id": document_id,
            "document_version_id": version_id,
            "status": "noop",
        }
