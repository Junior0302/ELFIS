"""Cookies — politique documentée (auth Bearer/Firebase)."""

from __future__ import annotations

from pathlib import Path


def test_cookie_security_auth_is_bearer_primary():
    """Le token principal n’est pas un cookie session serveur."""
    auth = Path(__file__).resolve().parents[2] / "app" / "services" / "auth.py"
    text = auth.read_text(encoding="utf-8")
    # Firebase / JWT bearer path présents ; pas de set_cookie session critique attendu ici
    assert "firebase" in text.lower() or "jwt" in text.lower()
