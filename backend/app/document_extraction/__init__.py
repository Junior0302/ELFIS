"""Document Extraction Engine V1 — propositions structurées (pas d'import métier)."""

from decimal import Decimal

EXTRACTION_ENGINE_VERSION = "1.0.0"
PROMPT_VERSION = "extract-structured-v1"
MAX_TEXT_CHARACTERS = 50_000
AMOUNT_TOLERANCE = Decimal("0.02")
