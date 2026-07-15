from __future__ import annotations

import re
from pathlib import Path

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}
PDF_EXT = {".pdf"}
ALLOWED_EXT = PDF_EXT | IMAGE_EXT

DOC_TYPE_RULES: list[tuple[str, list[str]]] = [
    ("avoir", [r"\bavoir\b", r"\bcredit\s*note\b", r"\bnote\s*de\s*cr[eé]dit\b"]),
    ("devis", [r"\bdevis\b", r"\bquotation\b", r"\bproforma\b", r"\bpro\s*forma\b"]),
    ("ticket", [r"\bticket\b", r"\bre[cç]u\b", r"\breceipt\b", r"\bcaisse\b"]),
    ("note_frais", [r"\bnote\s*de\s*frais\b", r"\bexpense\b", r"\bfrais\s*pro\b"]),
    ("releve", [r"\brelev[eé]\b", r"\bstatement\b"]),
    ("facture", [r"\bfacture\b", r"\binvoice\b", r"\bfac[-/]?\d"]),
]


def detect_document_type(text: str, filename: str = "") -> str:
    blob = f"{text}\n{filename}".lower()
    for doc_type, patterns in DOC_TYPE_RULES:
        for pattern in patterns:
            if re.search(pattern, blob, re.IGNORECASE):
                return doc_type
    return "facture"


def extract_text_from_file(path: Path) -> tuple[str, str]:
    """Retourne (texte, engine) pour PDF ou image."""
    ext = path.suffix.lower()
    if ext in PDF_EXT:
        return _extract_pdf(path), "pdf-text"
    if ext in IMAGE_EXT:
        return _extract_image(path)
    return "", "none"


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(p for p in parts if p.strip()).strip()
    except Exception:
        return ""


def _extract_image(path: Path) -> tuple[str, str]:
    # 1) OpenAI Vision si clé dispo
    from app.config import settings

    if settings.openai_api_key:
        text = _openai_vision_ocr(path)
        if text:
            return text, "openai-vision"

    # 2) Tesseract optionnel
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="fra+eng") or ""
        if text.strip():
            return text.strip(), "tesseract"
    except Exception:
        pass

    # 3) Fallback : métadonnées fichier (mode démo)
    return f"Image: {path.name}", "image-fallback"


def _openai_vision_ocr(path: Path) -> str:
    import base64
    import mimetypes

    try:
        from openai import OpenAI
        from app.config import settings

        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Tu es un OCR comptable. Extrais tout le texte lisible de cette "
                                "facture/photo (fournisseur, date, numéros, montants HT/TVA/TTC)."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                    ],
                }
            ],
            temperature=0,
            max_tokens=2000,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception:
        return ""
