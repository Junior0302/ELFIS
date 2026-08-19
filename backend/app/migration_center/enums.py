"""Enums / constantes Migration Center."""

from __future__ import annotations

from enum import Enum


class MigrationMode(str, Enum):
    INITIAL_MIGRATION = "initial_migration"
    ONE_TIME_IMPORT = "one_time_import"


class MigrationSessionStatus(str, Enum):
    DRAFT = "draft"
    PROFILE_COMPLETED = "profile_completed"
    SOURCES_SELECTED = "sources_selected"
    AWAITING_UPLOAD = "awaiting_upload"
    ANALYZING = "analyzing"
    ANALYSIS_COMPLETED = "analysis_completed"
    AWAITING_VALIDATION = "awaiting_validation"
    READY_TO_IMPORT = "ready_to_import"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


SPRINT1_STATUSES = frozenset(
    {
        MigrationSessionStatus.DRAFT.value,
        MigrationSessionStatus.PROFILE_COMPLETED.value,
        MigrationSessionStatus.SOURCES_SELECTED.value,
        MigrationSessionStatus.AWAITING_UPLOAD.value,
        MigrationSessionStatus.CANCELLED.value,
    }
)

TERMINAL_INACTIVE = frozenset(
    {
        MigrationSessionStatus.COMPLETED.value,
        MigrationSessionStatus.FAILED.value,
        MigrationSessionStatus.CANCELLED.value,
    }
)

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    MigrationSessionStatus.DRAFT.value: frozenset(
        {MigrationSessionStatus.PROFILE_COMPLETED.value, MigrationSessionStatus.CANCELLED.value}
    ),
    MigrationSessionStatus.PROFILE_COMPLETED.value: frozenset(
        {MigrationSessionStatus.SOURCES_SELECTED.value, MigrationSessionStatus.CANCELLED.value}
    ),
    MigrationSessionStatus.SOURCES_SELECTED.value: frozenset(
        {MigrationSessionStatus.AWAITING_UPLOAD.value, MigrationSessionStatus.CANCELLED.value}
    ),
    MigrationSessionStatus.AWAITING_UPLOAD.value: frozenset(
        {MigrationSessionStatus.CANCELLED.value}
    ),
}

CANCELABLE_STATUSES = frozenset(
    {
        MigrationSessionStatus.DRAFT.value,
        MigrationSessionStatus.PROFILE_COMPLETED.value,
        MigrationSessionStatus.SOURCES_SELECTED.value,
        MigrationSessionStatus.AWAITING_UPLOAD.value,
    }
)

# Wizard steps (1-based) — Sprint 1 UI
STEP_WELCOME = 1
STEP_PROFILE = 2
STEP_SOURCES = 3
STEP_ANALYSIS = 4
STEP_VALIDATION = 5
STEP_IMPORT = 6
STEP_DONE = 7

STATUS_TO_STEP = {
    MigrationSessionStatus.DRAFT.value: STEP_WELCOME,
    MigrationSessionStatus.PROFILE_COMPLETED.value: STEP_PROFILE,
    MigrationSessionStatus.SOURCES_SELECTED.value: STEP_SOURCES,
    MigrationSessionStatus.AWAITING_UPLOAD.value: STEP_SOURCES,
}


class TimelineStepKey(str, Enum):
    WELCOME = "welcome"
    COMPANY_PROFILE = "company_profile"
    DATA_SOURCES = "data_sources"
    UPLOAD_PREPARATION = "upload_preparation"
    FILE_UPLOAD = "file_upload"
    ANALYSIS = "analysis"
    VALIDATION = "validation"
    IMPORT = "import"
    COMPLETION = "completion"


TIMELINE_STEP_ORDER: dict[str, int] = {
    TimelineStepKey.WELCOME.value: 1,
    TimelineStepKey.COMPANY_PROFILE.value: 2,
    TimelineStepKey.DATA_SOURCES.value: 3,
    TimelineStepKey.UPLOAD_PREPARATION.value: 4,
    TimelineStepKey.FILE_UPLOAD.value: 5,
    TimelineStepKey.ANALYSIS.value: 6,
    TimelineStepKey.VALIDATION.value: 7,
    TimelineStepKey.IMPORT.value: 8,
    TimelineStepKey.COMPLETION.value: 9,
}

ALL_TIMELINE_STEPS: tuple[str, ...] = tuple(TIMELINE_STEP_ORDER.keys())


class TimelineEntryStatus(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ActivityType(str, Enum):
    MIGRATION_CREATED = "migration_created"
    PROFILE_SAVED = "profile_saved"
    SOURCES_SAVED = "sources_saved"
    STEP_COMPLETED = "step_completed"
    MIGRATION_RESUMED = "migration_resumed"
    MIGRATION_CANCELLED = "migration_cancelled"
    MIGRATION_CONFLICT_DETECTED = "migration_conflict_detected"


class ActivitySeverity(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class ActivityActorType(str, Enum):
    USER = "user"
    SYSTEM = "system"
    AI = "ai"
    WORKER = "worker"
    ADMIN = "admin"


class CompanyAgeRange(str, Enum):
    STARTING_TODAY = "starting_today"
    LESS_THAN_6_MONTHS = "less_than_6_months"
    BETWEEN_6_MONTHS_AND_2_YEARS = "between_6_months_and_2_years"
    MORE_THAN_2_YEARS = "more_than_2_years"


class LegalForm(str, Enum):
    MICRO_ENTERPRISE = "micro_enterprise"
    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    EURL = "eurl"
    SARL = "sarl"
    SASU = "sasu"
    SAS = "sas"
    ASSOCIATION = "association"
    OTHER = "other"


class TeamSize(str, Enum):
    ONE = "one"
    TWO_TO_FIVE = "two_to_five"
    SIX_TO_TWENTY = "six_to_twenty"
    MORE_THAN_TWENTY = "more_than_twenty"


class AccountantStatus(str, Enum):
    HAS_ACCOUNTANT = "has_accountant"
    NO_ACCOUNTANT = "no_accountant"
    LOOKING_FOR_ACCOUNTANT = "looking_for_accountant"


class JoinReason(str, Enum):
    CREATING_BUSINESS = "creating_business"
    CHANGING_SOFTWARE = "changing_software"
    SAVING_TIME = "saving_time"
    CURRENT_SOFTWARE_TOO_EXPENSIVE = "current_software_too_expensive"
    USING_AI = "using_ai"
    OTHER = "other"


class SourceAvailability(str, Enum):
    AVAILABLE = "available"
    COMING_SOON = "coming_soon"
    UNAVAILABLE = "unavailable"
    BETA = "beta"
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"


# Sélection nouvelle session : autorisée
SELECTABLE_AVAILABILITIES = frozenset(
    {
        SourceAvailability.AVAILABLE.value,
        SourceAvailability.BETA.value,
    }
)

# Interdites pour une nouvelle sélection
BLOCKED_NEW_SELECTION = frozenset(
    {
        SourceAvailability.COMING_SOON.value,
        SourceAvailability.UNAVAILABLE.value,
        SourceAvailability.MAINTENANCE.value,
        SourceAvailability.DEPRECATED.value,
    }
)

EMPTY_PROFILE_ENVELOPE: dict = {"schema_version": 1, "data": {}}
