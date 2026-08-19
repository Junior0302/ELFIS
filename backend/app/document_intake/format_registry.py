"""Registre extensible des formats acceptés — Document Intake."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FormatDef:
    id: str
    label: str
    extensions: tuple[str, ...]
    mime_types: tuple[str, ...]
    max_bytes: int
    upload_allowed: bool = True
    preview_allowed: bool = False
    analysis_allowed: bool = False  # futur — jamais vrai pour ZIP en V1
    extract_later: bool = False
    metadata: dict = field(default_factory=lambda: {"schema_version": 1})


# Tailles par type (plafond module = 15 MiB sauf config)
_M = 1024 * 1024

FORMAT_REGISTRY: tuple[FormatDef, ...] = (
    FormatDef("pdf", "PDF", (".pdf",), ("application/pdf",), 15 * _M, preview_allowed=True),
    FormatDef(
        "csv",
        "CSV",
        (".csv",),
        ("text/csv", "application/csv", "text/plain"),
        15 * _M,
        preview_allowed=True,
    ),
    FormatDef(
        "xls",
        "Excel 97-2003",
        (".xls",),
        ("application/vnd.ms-excel", "application/octet-stream"),
        15 * _M,
    ),
    FormatDef(
        "xlsx",
        "Excel",
        (".xlsx",),
        (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/zip",
        ),
        15 * _M,
    ),
    FormatDef(
        "ods",
        "OpenDocument Spreadsheet",
        (".ods",),
        ("application/vnd.oasis.opendocument.spreadsheet", "application/zip"),
        15 * _M,
    ),
    FormatDef(
        "xml",
        "XML",
        (".xml",),
        ("application/xml", "text/xml"),
        15 * _M,
        preview_allowed=True,
    ),
    FormatDef(
        "json",
        "JSON",
        (".json",),
        ("application/json", "text/plain"),
        15 * _M,
        preview_allowed=True,
    ),
    FormatDef(
        "zip",
        "ZIP",
        (".zip",),
        ("application/zip", "application/x-zip-compressed"),
        15 * _M,
        preview_allowed=False,
        analysis_allowed=False,
        extract_later=True,
    ),
    FormatDef("jpeg", "JPEG", (".jpg", ".jpeg"), ("image/jpeg",), 15 * _M, preview_allowed=True),
    FormatDef("png", "PNG", (".png",), ("image/png",), 15 * _M, preview_allowed=True),
    FormatDef(
        "tiff",
        "TIFF",
        (".tif", ".tiff"),
        ("image/tiff", "image/tif"),
        15 * _M,
        preview_allowed=True,
    ),
    FormatDef("txt", "Texte", (".txt",), ("text/plain",), 5 * _M, preview_allowed=True),
)

_BY_EXT: dict[str, FormatDef] = {}
for _f in FORMAT_REGISTRY:
    for _e in _f.extensions:
        _BY_EXT[_e.lower()] = _f


def list_formats() -> list[dict]:
    return [
        {
            "id": f.id,
            "label": f.label,
            "extensions": list(f.extensions),
            "mime_types": list(f.mime_types),
            "max_bytes": f.max_bytes,
            "upload_allowed": f.upload_allowed,
            "preview_allowed": f.preview_allowed,
            "analysis_allowed": f.analysis_allowed,
            "extract_later": f.extract_later,
            "metadata": dict(f.metadata),
        }
        for f in FORMAT_REGISTRY
        if f.upload_allowed
    ]


def get_format_by_extension(ext: str) -> FormatDef | None:
    key = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
    return _BY_EXT.get(key)


def accepted_extensions() -> frozenset[str]:
    return frozenset(_BY_EXT.keys())
