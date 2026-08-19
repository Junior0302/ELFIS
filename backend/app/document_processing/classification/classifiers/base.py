"""Contrat classifiers + résultats."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.storage.storage_models import (
    ElfisDocumentLink,
    ElfisDocumentRecord,
    ElfisDocumentVersion,
    ElfisStorageObject,
)


@dataclass
class ClassificationEvidence:
    code: str
    detail: str | None = None
    weight: float = 0.0


@dataclass
class ClassificationAlternative:
    type_key: str
    score: float


@dataclass
class DocumentClassificationResult:
    predicted_type: str
    confidence_score: float
    alternatives: list[ClassificationAlternative] = field(default_factory=list)
    evidence: list[ClassificationEvidence] = field(default_factory=list)
    requires_review: bool = True
    classifier_key: str = ""
    classifier_version: str = ""
    error_code: str | None = None


@dataclass
class ClassificationContext:
    db: Session
    document: ElfisDocumentRecord
    version: ElfisDocumentVersion
    storage_object: ElfisStorageObject | None
    links: list[ElfisDocumentLink] = field(default_factory=list)
    job_id: str | None = None
    organization_id: int = 0


class DocumentClassifier(Protocol):
    classifier_key: str
    classifier_version: str

    async def classify(self, context: ClassificationContext) -> DocumentClassificationResult: ...
