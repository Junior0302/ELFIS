"""Analyse technique — format réel, PDF, ZIP, etc. (lecture seule)."""

from __future__ import annotations

import io
import zipfile
from typing import Any


def _pdf_info(content: bytes) -> dict[str, Any]:
    info: dict[str, Any] = {
        "is_pdf": content[:5] == b"%PDF-",
        "pdf_version": None,
        "has_text": False,
        "has_images": False,
        "is_encrypted": False,
        "is_protected": False,
        "probable_scan": False,
        "page_count": None,
        "producer": None,
    }
    if not info["is_pdf"]:
        return info
    head = content[:32].decode("latin-1", errors="ignore")
    if head.startswith("%PDF-"):
        info["pdf_version"] = head[5:8].strip()
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content), strict=False)
        info["is_encrypted"] = bool(reader.is_encrypted)
        info["is_protected"] = bool(reader.is_encrypted)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return info
        info["page_count"] = len(reader.pages)
        meta = reader.metadata
        if meta:
            info["producer"] = str(getattr(meta, "producer", None) or "") or None
        text_chars = 0
        image_xobjects = 0
        for page in reader.pages[:50]:
            try:
                t = page.extract_text() or ""
                text_chars += len(t.strip())
            except Exception:
                pass
            try:
                resources = page.get("/Resources")
                if resources and "/XObject" in resources:
                    xobj = resources["/XObject"]
                    if hasattr(xobj, "get_object"):
                        xobj = xobj.get_object()
                    for key in xobj:
                        try:
                            obj = xobj[key]
                            if hasattr(obj, "get_object"):
                                obj = obj.get_object()
                            if obj.get("/Subtype") == "/Image":
                                image_xobjects += 1
                        except Exception:
                            continue
            except Exception:
                pass
        info["has_text"] = text_chars > 40
        info["has_images"] = image_xobjects > 0
        # Scan probable : beaucoup d'images, peu de texte
        if info["page_count"] and info["page_count"] > 0:
            if text_chars < 40 and (image_xobjects > 0 or len(content) > 50_000):
                info["probable_scan"] = True
            elif text_chars < 20:
                info["probable_scan"] = True
    except Exception as exc:
        info["parse_error"] = type(exc).__name__
        # Heuristique brute
        raw = content[:200_000]
        info["has_text"] = b"/Font" in raw and b"BT" in raw
        info["has_images"] = b"/Image" in raw or b"/XObject" in raw
        info["is_encrypted"] = b"/Encrypt" in raw
        info["is_protected"] = info["is_encrypted"]
        info["probable_scan"] = not info["has_text"] and info["has_images"]
    return info


def _detect_format(content: bytes, mime: str | None, extension: str | None) -> str:
    if content[:5] == b"%PDF-":
        return "pdf"
    if content[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if content[:2] == b"PK":
        return "zip"
    if content[:5] == b"<?xml" or content.lstrip()[:1] == b"<":
        return "xml"
    ext = (extension or "").lower().lstrip(".")
    if ext in {"csv", "json", "xml", "txt", "xls", "xlsx", "ods", "tiff", "tif"}:
        return ext if ext != "tif" else "tiff"
    if mime:
        mapping = {
            "application/pdf": "pdf",
            "image/jpeg": "jpeg",
            "image/png": "png",
            "application/zip": "zip",
            "text/csv": "csv",
            "application/json": "json",
            "application/xml": "xml",
            "text/xml": "xml",
        }
        if mime in mapping:
            return mapping[mime]
    # JSON / CSV heuristique
    sample = content[:2000].lstrip()
    if sample.startswith((b"{", b"[")):
        return "json"
    if b"," in sample and b"\n" in sample:
        return "csv"
    return ext or "unknown"


def analyze_technical(
    content: bytes,
    *,
    mime: str | None = None,
    extension: str | None = None,
) -> dict[str, Any]:
    fmt = _detect_format(content, mime, extension)
    pdf = _pdf_info(content) if fmt == "pdf" else {
        "is_pdf": False,
        "pdf_version": None,
        "has_text": False,
        "has_images": fmt in {"jpeg", "png", "tiff"},
        "is_encrypted": False,
        "is_protected": False,
        "probable_scan": fmt in {"jpeg", "png", "tiff"},
        "page_count": 1 if fmt in {"jpeg", "png", "tiff"} else None,
        "producer": None,
    }
    zip_info: dict[str, Any] = {"is_zip": fmt == "zip", "entry_count": None}
    if fmt == "zip":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                names = zf.namelist()[:10_000]
                zip_info["entry_count"] = len(names)
        except zipfile.BadZipFile:
            zip_info["malformed"] = True

    return {
        "detected_format": fmt,
        "size_bytes": len(content),
        "mime_hint": mime,
        "pdf": pdf,
        "zip": zip_info,
        "is_xml": fmt == "xml",
        "is_csv": fmt == "csv",
        "is_json": fmt == "json",
        "is_image": fmt in {"jpeg", "png", "tiff"},
    }
