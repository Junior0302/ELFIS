"""Enums Validation & Mapping."""

from __future__ import annotations

from enum import Enum


class ValidationSessionStatus(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    VALIDATED = "validated"
    READY_FOR_IMPORT = "ready_for_import"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class FieldValidationStatus(str, Enum):
    UNKNOWN = "unknown"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


class MatchCategory(str, Enum):
    EXACT = "exact"
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"
    NO_MATCH = "no_match"


class MatchResolution(str, Enum):
    UNRESOLVED = "unresolved"
    USE_EXISTING = "use_existing"
    CREATE_LATER = "create_later"
    IGNORE = "ignore"


class DuplicateSeverity(str, Enum):
    EXACT = "exact"
    PROBABLE = "probable"
    WEAK = "weak"
