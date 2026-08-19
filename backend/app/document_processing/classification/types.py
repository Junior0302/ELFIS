"""Types classification documentaire RC2.5.2 — heuristiques, pas de probabilités."""

from __future__ import annotations

from enum import Enum


class ClassificationStatus(str, Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    FAILED = "failed"


CLASSIFIER_COMPOSITE_KEY = "composite_deterministic"
CLASSIFIER_COMPOSITE_VERSION = "1.0.0"

PIPELINE_CLASSIFICATION_V1 = "document_classification_v1"
STEP_CLASSIFY = "classify_document"
STEP_PERSIST_CLASSIFICATION = "persist_classification"

# Type générique facture sans direction fournisseur/client
TYPE_INVOICE = "invoice"
