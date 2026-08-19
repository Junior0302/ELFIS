"""Sanitisation OCR — jamais de texte OCR dans messages/logs."""

from __future__ import annotations

from typing import Any


def sanitize_ocr_error(message: str | None, *, max_len: int = 200) -> str:
    text = (message or "ocr_error").strip()
    # ne jamais laisser passer de longues chaînes (risque de texte OCR)
    if len(text) > max_len:
        text = text[:max_len]
    return text


def sanitize_warnings(items: list[Any] | None, *, max_items: int = 20) -> list[str]:
    out: list[str] = []
    for item in items or []:
        code = str(item)[:64].strip()
        if code:
            out.append(code)
        if len(out) >= max_items:
            break
    return out


def round_confidence(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, round(float(value), 4)))
