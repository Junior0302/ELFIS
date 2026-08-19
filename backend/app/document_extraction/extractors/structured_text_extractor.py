"""Extracteur fichiers structurés JSON/CSV/XML."""

from __future__ import annotations

import csv
import io
import json
from typing import Any
from xml.etree import ElementTree

from app.document_extraction.enums import FieldSource


def extract_structured(
    content: bytes,
    *,
    fmt: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    data: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    if fmt == "json":
        try:
            parsed = json.loads(content.decode("utf-8", errors="ignore"))
            if isinstance(parsed, dict):
                data = parsed
                for k in list(data.keys())[:50]:
                    provenance[k] = {
                        "field_path": k,
                        "value": data[k],
                        "raw_value": data[k],
                        "source": FieldSource.STRUCTURED_FILE.value,
                        "page_number": None,
                        "extractor_name": "structured_text_extractor",
                        "extractor_version": "1.0",
                        "confidence": 0.95,
                        "warnings": [],
                    }
        except Exception:
            return {}, {}
    elif fmt == "csv":
        try:
            text = content.decode("utf-8", errors="ignore")
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)[:500]
            data = {"line_items": rows, "row_count": len(rows)}
            provenance["line_items"] = {
                "field_path": "line_items",
                "value": rows,
                "raw_value": f"{len(rows)}_rows",
                "source": FieldSource.STRUCTURED_FILE.value,
                "extractor_name": "structured_text_extractor",
                "extractor_version": "1.0",
                "confidence": 0.9,
                "warnings": [],
                "page_number": None,
            }
        except Exception:
            return {}, {}
    elif fmt == "xml":
        try:
            root = ElementTree.fromstring(content)
            flat = {child.tag: (child.text or "").strip() for child in list(root)[:100]}
            data = flat
            for k, v in flat.items():
                provenance[k] = {
                    "field_path": k,
                    "value": v,
                    "raw_value": v,
                    "source": FieldSource.STRUCTURED_FILE.value,
                    "extractor_name": "structured_text_extractor",
                    "extractor_version": "1.0",
                    "confidence": 0.9,
                    "warnings": [],
                    "page_number": None,
                }
        except Exception:
            return {}, {}
    return data, provenance
