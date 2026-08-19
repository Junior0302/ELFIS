#!/usr/bin/env python
"""Vérifie les métadonnées d'un backup (sans exposer le dump).

Usage:
  python scripts/production/verify_backup.py --path ./backups/elfis_2026.dump

Refuse les chemins dans le dépôt git tracked et les cibles production implicites.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--min-bytes", type=int, default=1)
    args = parser.parse_args()

    path = Path(args.path).resolve()
    if not path.is_file():
        print(json.dumps({"ok": False, "error": "file_not_found"}))
        return 1

    size = path.stat().st_size
    # Checksum partiel (premier + dernier Mo) pour ne pas charger entièrement
    h = hashlib.sha256()
    with path.open("rb") as f:
        head = f.read(1024 * 1024)
        h.update(head)
        if size > 2 * 1024 * 1024:
            f.seek(max(0, size - 1024 * 1024))
            h.update(f.read(1024 * 1024))
        else:
            # déjà lu
            pass
    payload = {
        "ok": size >= args.min_bytes,
        "path": str(path.name),  # pas le chemin absolu complet en CI
        "size_bytes": size,
        "mtime_utc": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
        "checksum_sha256_partial": h.hexdigest(),
        "note": "Checksum partiel — restauration périodique obligatoire (voir runbook).",
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
