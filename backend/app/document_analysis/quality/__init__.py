"""Score qualité 0–100 — heuristiques légères."""

from __future__ import annotations

import io
from typing import Any


def analyze_quality(
    content: bytes,
    technical: dict[str, Any],
    pages: dict[str, Any],
    orientation: dict[str, Any],
) -> dict[str, Any]:
    score = 70
    details: dict[str, Any] = {
        "resolution_score": None,
        "contrast_score": None,
        "rotation_penalty": 0,
        "readability_score": None,
        "empty_pages_penalty": 0,
        "blur_penalty": 0,
        "text_density_score": None,
    }
    fmt = technical.get("detected_format")
    pdf = technical.get("pdf") or {}

    if orientation.get("mixed"):
        score -= 15
        details["rotation_penalty"] = 15
    elif orientation.get("degrees") not in (0, None):
        score -= 8
        details["rotation_penalty"] = 8

    if fmt == "pdf":
        if pdf.get("is_encrypted"):
            score -= 25
        if pdf.get("has_text"):
            score += 15
            details["text_density_score"] = 80
            details["readability_score"] = 85
        elif pdf.get("probable_scan"):
            score -= 10
            details["text_density_score"] = 20
            details["readability_score"] = 45
        if pdf.get("has_images") and not pdf.get("has_text"):
            details["contrast_score"] = 50
        else:
            details["contrast_score"] = 70

    if technical.get("is_image"):
        try:
            from PIL import Image, ImageStat

            img = Image.open(io.BytesIO(content)).convert("L")
            w, h = img.size
            mp = (w * h) / 1_000_000.0
            if mp >= 2:
                details["resolution_score"] = 90
                score += 10
            elif mp >= 0.5:
                details["resolution_score"] = 70
                score += 5
            else:
                details["resolution_score"] = 40
                score -= 15
            stat = ImageStat.Stat(img)
            # Écart-type comme proxy contraste
            std = float(stat.stddev[0]) if stat.stddev else 0
            details["contrast_score"] = min(100, int(std * 2))
            if std < 20:
                score -= 15
                details["blur_penalty"] = 15
            elif std < 35:
                score -= 5
            details["readability_score"] = details["contrast_score"]
        except Exception:
            details["resolution_score"] = 50

    if fmt in {"csv", "json", "xml", "txt"}:
        score = 90
        details["readability_score"] = 95
        details["text_density_score"] = 95

    if technical.get("zip", {}).get("malformed"):
        score -= 30

    empty = int(pages.get("empty_page_estimate") or 0)
    if empty:
        details["empty_pages_penalty"] = min(20, empty * 5)
        score -= details["empty_pages_penalty"]

    score = max(0, min(100, int(score)))
    return {
        "score": score,
        "band": "high" if score >= 75 else ("medium" if score >= 45 else "low"),
        "details": details,
    }
