"""Highlighting / snippets sûrs."""

from __future__ import annotations

import html
import re

from app.config import settings


def build_snippet(text: str | None, query: str | None, *, max_len: int | None = None) -> str:
    """
    Extrait limité avec marqueurs sûrs [[ ]] autour des termes.
    Aucun HTML non échappé — le résultat est du texte échappé.
    """
    source = (text or "").strip()
    if not source:
        return ""
    limit = max_len or max(40, int(settings.elfis_search_snippet_length))
    q = (query or "").strip()
    # Choisir une fenêtre autour du premier match
    window_start = 0
    terms = [t for t in re.split(r"\s+", q) if len(t) >= 2] if q else []
    lowered = source.lower()
    for term in terms:
        idx = lowered.find(term.lower())
        if idx >= 0:
            window_start = max(0, idx - limit // 3)
            break
    chunk = source[window_start : window_start + limit]
    if window_start > 0:
        chunk = "…" + chunk
    if window_start + limit < len(source):
        chunk = chunk + "…"

    escaped = html.escape(chunk, quote=True)
    for term in sorted(terms, key=len, reverse=True):
        if not term:
            continue
        pattern = re.compile(re.escape(html.escape(term, quote=True)), re.IGNORECASE)
        escaped = pattern.sub(lambda m: f"[[{m.group(0)}]]", escaped)
    return escaped
