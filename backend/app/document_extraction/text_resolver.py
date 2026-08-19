"""DocumentTextResolver — meilleur texte exploitable (sans inventer)."""

from __future__ import annotations

import io
import json
import re
from typing import Any

from app.document_extraction import MAX_TEXT_CHARACTERS

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _clean(text: str) -> str:
    text = _CONTROL.sub(" ", text)
    if len(text) > MAX_TEXT_CHARACTERS:
        return text[:MAX_TEXT_CHARACTERS]
    return text


def resolve_document_text(
    *,
    content: bytes,
    filename: str,
    mime: str | None,
    extension: str | None,
    analysis_report: dict[str, Any] | None,
    need_ocr: bool | None,
) -> dict[str, Any]:
    warnings: list[str] = []
    tech = (analysis_report or {}).get("technical") or {}
    fmt = tech.get("detected_format") or (extension or "").lstrip(".") or "unknown"
    lang = ((analysis_report or {}).get("language") or {}).get("code") or "unknown"

    # Texte OCR déjà produit (jamais inventé)
    ocr_block = (analysis_report or {}).get("ocr") or (analysis_report or {}).get("ocr_result") or {}
    ocr_text = ""
    if isinstance(ocr_block, dict):
        ocr_text = str(ocr_block.get("text") or ocr_block.get("full_text") or "")
    elif isinstance(ocr_block, str):
        ocr_text = ocr_block
    if ocr_text.strip():
        text = _clean(ocr_text)
        return {
            "source": "ocr",
            "text": text,
            "page_texts": [text],
            "language": lang,
            "character_count": len(text),
            "page_count": int(ocr_block.get("page_count") or 1) if isinstance(ocr_block, dict) else 1,
            "is_complete": True,
            "requires_ocr": False,
            "warnings": warnings,
        }

    # Structured text formats
    if fmt in {"csv", "json", "xml", "txt"} or (extension or "").lower() in {
        ".csv",
        ".json",
        ".xml",
        ".txt",
    }:
        raw = content.decode("utf-8", errors="ignore")
        text = _clean(raw)
        return {
            "source": "structured_file" if fmt != "txt" else "native_text",
            "text": text,
            "page_texts": [text] if text else [],
            "language": lang,
            "character_count": len(text),
            "page_count": 1,
            "is_complete": True,
            "requires_ocr": False,
            "warnings": warnings,
        }

    if fmt == "pdf" or (content[:5] == b"%PDF-"):
        page_texts: list[str] = []
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content), strict=False)
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    warnings.append("pdf_encrypted")
                    return {
                        "source": "native_pdf_text",
                        "text": "",
                        "page_texts": [],
                        "language": lang,
                        "character_count": 0,
                        "page_count": len(reader.pages) if reader.pages else 0,
                        "is_complete": False,
                        "requires_ocr": True,
                        "warnings": warnings,
                    }
            for page in reader.pages[:100]:
                try:
                    page_texts.append(page.extract_text() or "")
                except Exception:
                    page_texts.append("")
            text = _clean("\n".join(page_texts))
            requires = bool(need_ocr) or len(text.strip()) < 40
            if requires and len(text.strip()) < 40:
                warnings.append("insufficient_native_text")
            return {
                "source": "native_pdf_text",
                "text": text,
                "page_texts": page_texts,
                "language": lang,
                "character_count": len(text),
                "page_count": len(page_texts),
                "is_complete": not requires,
                "requires_ocr": requires and len(text.strip()) < 40,
                "warnings": warnings,
            }
        except Exception as exc:
            warnings.append(f"pdf_parse_{type(exc).__name__}")

    if fmt in {"jpeg", "png", "tiff"} or bool(need_ocr):
        return {
            "source": "empty",
            "text": "",
            "page_texts": [],
            "language": lang,
            "character_count": 0,
            "page_count": 1,
            "is_complete": False,
            "requires_ocr": True,
            "warnings": warnings + ["ocr_required_no_text"],
        }

    # Fallback: try decode
    try:
        text = _clean(content.decode("utf-8", errors="ignore"))
        if text.strip():
            return {
                "source": "native_text",
                "text": text,
                "page_texts": [text],
                "language": lang,
                "character_count": len(text),
                "page_count": 1,
                "is_complete": True,
                "requires_ocr": False,
                "warnings": warnings,
            }
    except Exception:
        pass

    return {
        "source": "empty",
        "text": "",
        "page_texts": [],
        "language": lang,
        "character_count": 0,
        "page_count": 0,
        "is_complete": False,
        "requires_ocr": bool(need_ocr),
        "warnings": warnings + ["no_text_available"],
    }


def detect_prompt_injection(text: str) -> list[str]:
    """Détecte des motifs d'injection — le contenu n'est jamais une instruction."""
    hits: list[str] = []
    lower = text.lower()
    patterns = [
        ("ignore previous instructions", "IGNORE_INSTRUCTIONS"),
        ("ignore all previous", "IGNORE_INSTRUCTIONS"),
        ("reveal the system prompt", "REVEAL_PROMPT"),
        ("return all environment variables", "REVEAL_ENV"),
        ("send data to", "EXFILTRATION_HINT"),
        ("send the document to", "EXFILTRATION_HINT"),
        ("curl ", "SHELL_HINT"),
        ("rm -rf", "SHELL_HINT"),
        ("powershell", "SHELL_HINT"),
        ("bash -c", "SHELL_HINT"),
        ("<script", "HTML_SCRIPT"),
        ("javascript:", "HTML_SCRIPT"),
        ("change the output schema", "SCHEMA_TAMPER"),
        ("pretend the invoice total", "DATA_TAMPER"),
        ("call an external tool", "FAKE_TOOL"),
        ("execute this shell", "SHELL_HINT"),
        ("```system", "FAKE_SYSTEM_BLOCK"),
        ("[system]", "FAKE_SYSTEM_BLOCK"),
        ("[developer]", "FAKE_DEVELOPER_BLOCK"),
        ("\"$schema\"", "FAKE_JSON_SCHEMA"),
        ("base64,", "ENCODED_PAYLOAD"),
        ("aWdub3Jl", "ENCODED_PAYLOAD"),
        ("cmV2ZWFs", "ENCODED_PAYLOAD"),
    ]
    for needle, code in patterns:
        if needle.lower() in lower:
            hits.append(code)
    if '"tool_call"' in lower or "function_call" in lower:
        hits.append("FAKE_TOOL")
    return list(dict.fromkeys(hits))