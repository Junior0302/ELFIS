"""Registry des sources de migration — règles de sélection centralisées."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.migration_center.enums import (
    BLOCKED_NEW_SELECTION,
    SELECTABLE_AVAILABILITIES,
    SourceAvailability,
)
from app.migration_center.exceptions import MigrationValidationError


@dataclass(frozen=True)
class MigrationSourceDef:
    id: str
    label: str
    category: str
    availability: str
    accepted_formats: tuple[str, ...]
    description: str
    capabilities: tuple[str, ...] = ()
    requires_connection: bool = False
    supports_folder: bool = False
    supports_incremental_import: bool = False
    supports_preview: bool = False
    metadata: dict = field(default_factory=lambda: {"schema_version": 1})


def _meta() -> dict:
    return {"schema_version": 1}


_SOURCES: tuple[MigrationSourceDef, ...] = (
    MigrationSourceDef(
        "file_excel",
        "Excel",
        "files",
        SourceAvailability.AVAILABLE.value,
        (".xlsx", ".xls"),
        "Fichiers tableurs Excel",
        capabilities=("upload", "preview"),
        supports_incremental_import=True,
        supports_preview=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "file_csv",
        "CSV",
        "files",
        SourceAvailability.AVAILABLE.value,
        (".csv",),
        "Fichiers CSV délimités",
        capabilities=("upload", "preview"),
        supports_incremental_import=True,
        supports_preview=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "file_pdf",
        "PDF",
        "files",
        SourceAvailability.AVAILABLE.value,
        (".pdf",),
        "Documents PDF",
        capabilities=("upload", "preview"),
        supports_incremental_import=True,
        supports_preview=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "file_zip",
        "ZIP",
        "files",
        SourceAvailability.AVAILABLE.value,
        (".zip",),
        "Archives ZIP",
        capabilities=("upload",),
        supports_folder=True,
        supports_incremental_import=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "file_xml",
        "XML",
        "files",
        SourceAvailability.AVAILABLE.value,
        (".xml",),
        "Fichiers XML",
        capabilities=("upload", "preview"),
        supports_incremental_import=True,
        supports_preview=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "file_json",
        "JSON",
        "files",
        SourceAvailability.AVAILABLE.value,
        (".json",),
        "Fichiers JSON",
        capabilities=("upload", "preview"),
        supports_incremental_import=True,
        supports_preview=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "complete_folder",
        "Dossier complet",
        "exports",
        SourceAvailability.AVAILABLE.value,
        (),
        "Dossier local regroupant plusieurs fichiers",
        capabilities=("upload",),
        supports_folder=True,
        supports_incremental_import=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "accounting_export",
        "Export comptable",
        "exports",
        SourceAvailability.AVAILABLE.value,
        (".csv", ".xlsx", ".xml"),
        "Export issu d’un logiciel comptable",
        capabilities=("upload", "preview"),
        supports_incremental_import=True,
        supports_preview=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "business_software_export",
        "Export d’un logiciel métier",
        "exports",
        SourceAvailability.AVAILABLE.value,
        (".csv", ".xlsx", ".json"),
        "Export issu d’un outil métier",
        capabilities=("upload", "preview"),
        supports_incremental_import=True,
        supports_preview=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "google_drive",
        "Google Drive",
        "cloud",
        SourceAvailability.COMING_SOON.value,
        (),
        "Connecteur Google Drive — bientôt disponible",
        capabilities=("connect",),
        requires_connection=True,
        supports_folder=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "onedrive",
        "OneDrive",
        "cloud",
        SourceAvailability.COMING_SOON.value,
        (),
        "Connecteur OneDrive — bientôt disponible",
        capabilities=("connect",),
        requires_connection=True,
        supports_folder=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "dropbox",
        "Dropbox",
        "cloud",
        SourceAvailability.COMING_SOON.value,
        (),
        "Connecteur Dropbox — bientôt disponible",
        capabilities=("connect",),
        requires_connection=True,
        supports_folder=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "other",
        "Autre",
        "other",
        SourceAvailability.AVAILABLE.value,
        (),
        "Autre source à préciser ultérieurement",
        capabilities=("upload",),
        metadata=_meta(),
    ),
    # Exemples d'états étendus (hors catalogue public si unavailable)
    MigrationSourceDef(
        "connector_beta_demo",
        "Connecteur expérimental",
        "cloud",
        SourceAvailability.BETA.value,
        (),
        "Connecteur en bêta — sélectionnable avec avertissement",
        capabilities=("connect", "preview"),
        requires_connection=True,
        supports_preview=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "connector_maintenance",
        "Connecteur en maintenance",
        "cloud",
        SourceAvailability.MAINTENANCE.value,
        (),
        "Temporairement indisponible",
        capabilities=("connect",),
        requires_connection=True,
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "legacy_import_v1",
        "Ancienne intégration",
        "other",
        SourceAvailability.DEPRECATED.value,
        (),
        "Encore lisible pour compatibilité — non recommandé",
        capabilities=("upload",),
        metadata=_meta(),
    ),
    MigrationSourceDef(
        "legacy_blocked",
        "Connecteur legacy (indisponible)",
        "other",
        SourceAvailability.UNAVAILABLE.value,
        (),
        "Source désactivée — non sélectionnable",
        metadata=_meta(),
    ),
)

_BY_ID = {s.id: s for s in _SOURCES}


def source_to_dict(s: MigrationSourceDef) -> dict:
    return {
        "id": s.id,
        "label": s.label,
        "category": s.category,
        "availability": s.availability,
        "accepted_formats": list(s.accepted_formats),
        "description": s.description,
        "capabilities": list(s.capabilities),
        "requires_connection": s.requires_connection,
        "supports_folder": s.supports_folder,
        "supports_incremental_import": s.supports_incremental_import,
        "supports_preview": s.supports_preview,
        "metadata": dict(s.metadata or {"schema_version": 1}),
    }


def list_source_catalog(*, include_unavailable: bool = False) -> list[dict]:
    items = []
    for s in _SOURCES:
        if s.availability == SourceAvailability.UNAVAILABLE.value and not include_unavailable:
            continue
        items.append(source_to_dict(s))
    return items


def get_source(source_id: str) -> MigrationSourceDef | None:
    return _BY_ID.get(source_id)


def is_selectable_for_new_session(availability: str) -> bool:
    return availability in SELECTABLE_AVAILABILITIES


def is_selection_blocked(availability: str) -> bool:
    return availability in BLOCKED_NEW_SELECTION


def can_keep_existing_source(source_id: str, previously_selected: list[str] | None) -> bool:
    """Deprecated tolérée si déjà présente sur une ancienne session."""
    src = get_source(source_id)
    if not src:
        return False
    if src.availability == SourceAvailability.DEPRECATED.value:
        return bool(previously_selected and source_id in previously_selected)
    return is_selectable_for_new_session(src.availability)


def validate_selected_sources(
    source_ids: list[str],
    *,
    require_available: bool = False,
    previously_selected: list[str] | None = None,
) -> list[str]:
    if not source_ids:
        raise MigrationValidationError("sources_required", "Au moins une source est requise")
    seen: set[str] = set()
    cleaned: list[str] = []
    prev = list(previously_selected or [])
    for sid in source_ids:
        if not isinstance(sid, str) or not sid.strip():
            raise MigrationValidationError("source_invalid", "Identifiant de source invalide")
        key = sid.strip()
        if key in seen:
            continue
        seen.add(key)
        src = get_source(key)
        if src is None:
            raise MigrationValidationError("source_unknown", f"Source inconnue: {key}")

        avail = src.availability
        if avail == SourceAvailability.UNAVAILABLE.value:
            raise MigrationValidationError("source_unavailable", f"Source indisponible: {key}")
        if avail == SourceAvailability.COMING_SOON.value:
            raise MigrationValidationError(
                "source_coming_soon",
                f"Source bientôt disponible — sélection interdite: {key}",
            )
        if avail == SourceAvailability.MAINTENANCE.value:
            raise MigrationValidationError(
                "source_maintenance",
                f"Source en maintenance: {key}",
            )
        if avail == SourceAvailability.DEPRECATED.value:
            if key in prev:
                cleaned.append(key)
                continue
            raise MigrationValidationError(
                "source_deprecated",
                f"Source dépréciée — non sélectionnable pour une nouvelle session: {key}",
            )
        if avail not in SELECTABLE_AVAILABILITIES:
            raise MigrationValidationError(
                "source_not_selectable",
                f"Source non sélectionnable: {key}",
            )
        cleaned.append(key)

    if not cleaned:
        raise MigrationValidationError("sources_required", "Au moins une source est requise")

    if require_available:
        has_usable = any(
            get_source(s) and get_source(s).availability in SELECTABLE_AVAILABILITIES  # type: ignore[union-attr]
            for s in cleaned
        )
        if not has_usable:
            has_legacy = any(
                get_source(s)
                and get_source(s).availability == SourceAvailability.DEPRECATED.value  # type: ignore[union-attr]
                and s in prev
                for s in cleaned
            )
            if not has_legacy:
                raise MigrationValidationError(
                    "sources_no_available",
                    "Sélectionnez au moins une source disponible (les connecteurs cloud arrivent bientôt)",
                )
    return cleaned
