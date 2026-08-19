"""Détection d'orientation — sans correction."""

from __future__ import annotations

import io
from typing import Any


def analyze_orientation(content: bytes, technical: dict[str, Any]) -> dict[str, Any]:
    """Retourne degrees ∈ {0, 90, 180, 270} ou mixed."""
    fmt = technical.get("detected_format")
    result: dict[str, Any] = {
        "degrees": 0,
        "mixed": False,
        "confidence": 0.5,
        "method": "default",
    }
    if fmt in {"jpeg", "png", "tiff"}:
        try:
            from PIL import Image, ExifTags

            img = Image.open(io.BytesIO(content))
            orientation = 0
            exif = img.getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag == "Orientation":
                        # EXIF: 3=180, 6=90 CW, 8=270 CW
                        mapping = {1: 0, 3: 180, 6: 90, 8: 270}
                        orientation = mapping.get(int(value), 0)
                        break
            w, h = img.size
            if orientation == 0 and h > w * 1.3:
                # portrait probable 0°
                result["confidence"] = 0.6
            result["degrees"] = orientation
            result["method"] = "exif_or_geometry"
            result["confidence"] = 0.85 if orientation else 0.55
            return result
        except Exception:
            return result

    if fmt == "pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content), strict=False)
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    return result
            rotations: list[int] = []
            for page in reader.pages[:30]:
                try:
                    rot = int(page.get("/Rotate") or 0) % 360
                    if rot not in (0, 90, 180, 270):
                        rot = 0
                    rotations.append(rot)
                except Exception:
                    rotations.append(0)
            if not rotations:
                return result
            unique = set(rotations)
            if len(unique) > 1:
                result["mixed"] = True
                result["degrees"] = rotations[0]
                result["confidence"] = 0.7
                result["method"] = "pdf_rotate_mixed"
            else:
                result["degrees"] = rotations[0]
                result["confidence"] = 0.9
                result["method"] = "pdf_rotate"
            return result
        except Exception:
            return result

    return result
