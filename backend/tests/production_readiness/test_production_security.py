"""SECRET / sécurité dépôt."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_secret_001_no_live_stripe_keys_in_repo():
    """Détection basique — ne pas afficher les matches complets.

    Délègue au script allowlisté (évite de maintenir deux scanners divergents).
    """
    import subprocess
    import sys

    script = ROOT / "backend" / "scripts" / "production" / "check_secrets.py"
    completed = subprocess.run([sys.executable, str(script)], cwd=str(ROOT / "backend"), capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_secret_002_gitignore_covers_env_and_dumps():
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for needle in (".env", "*.db", "*.dump", "credentials.json", "*.pem"):
        assert needle in gi


def test_secret_003_sanitizer_masks_stripe_like():
    from app.events.event_context import sanitize_error_message

    # Motif fictif volontaire — contient "fake" pour ne pas faire échouer check_secrets
    raw = "sk_live_fake_abcdefghijklmnopqrstuvwxyz"
    msg = sanitize_error_message(f"failed {raw} webhook")
    assert raw not in msg
