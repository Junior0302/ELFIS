#!/usr/bin/env python
"""Détection de secrets suspects dans le dépôt (sortie masquée).

Allowlist limitée pour faux positifs (fake / example / change-me).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

PATTERNS = [
    ("stripe_live", re.compile(r"sk_live_[A-Za-z0-9]{16,}")),
    ("stripe_restricted_live", re.compile(r"rk_live_[A-Za-z0-9]{16,}")),
    ("stripe_webhook", re.compile(r"whsec_[A-Za-z0-9]{16,}")),
    ("github_pat", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_key", re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----")),
]

ALLOW = ("fake", "example", "change-me", "test_only", "xxxxxxxx", "your_", "placeholder")
SKIP_PARTS = {".git", "node_modules", ".venv", "venv", "dist", "__pycache__", "coverage", "htmlcov"}
TEXT_SUFFIX = {
    ".py", ".md", ".ts", ".tsx", ".js", ".json", ".yml", ".yaml", ".toml",
    ".env", ".example", ".txt", ".cfg", ".ini", ".sql", ".sh", ".ps1",
}


def _allowed(value: str) -> bool:
    low = value.lower()
    return any(a in low for a in ALLOW)


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return value[:4] + "…" + value[-2:]


def main() -> int:
    hits: list[dict] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(p in path.parts for p in SKIP_PARTS):
            continue
        if path.suffix.lower() not in TEXT_SUFFIX and path.name not in {".env.example", "Dockerfile"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for kind, pat in PATTERNS:
            for m in pat.finditer(text):
                raw = m.group(0)
                if _allowed(raw):
                    continue
                rel = path.relative_to(ROOT).as_posix()
                hits.append({"kind": kind, "file": rel, "preview": _mask(raw)})
    if hits:
        print(f"FAIL: {len(hits)} secret(s) suspect(s)")
        for h in hits[:50]:
            print(f"  [{h['kind']}] {h['file']}: {h['preview']}")
        return 1
    print("OK: aucun secret suspect détecté")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
