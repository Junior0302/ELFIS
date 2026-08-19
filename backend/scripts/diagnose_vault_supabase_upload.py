"""Diagnostic sécurisé Vault ↔ Supabase Storage (pas de secrets, pas de facture réelle).

Usage (depuis backend/) :
  python -m scripts.diagnose_vault_supabase_upload

Étapes : config → list buckets → upload PDF factice → sign → download → delete.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Permet l'exécution directe depuis backend/
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.config import settings  # noqa: E402
from app.core.supabase_storage_client import (  # noqa: E402
    SupabaseStorageClient,
    SupabaseStorageError,
)


MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _print(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main() -> int:
    bucket = (settings.elfis_vault_bucket or "").strip() or "elfis-vault"
    client = SupabaseStorageClient()
    report: dict = {
        "bucket": bucket,
        "config": client.config_diagnostics(),
        "steps": {},
    }

    if not client.configured:
        report["status"] = "NO_GO"
        report["cause"] = "vault_storage_not_configured"
        _print(report)
        return 2

    # 1) Buckets
    try:
        buckets = client.list_buckets()
        names = [b.get("id") or b.get("name") for b in buckets]
        vault_meta = next(
            (b for b in buckets if (b.get("id") or b.get("name")) == bucket),
            None,
        )
        report["steps"]["list_buckets"] = {
            "ok": True,
            "bucket_present": bucket in names,
            "bucket_public": (vault_meta or {}).get("public") if vault_meta else None,
            "bucket_count": len(names),
        }
        if bucket not in names:
            report["status"] = "NO_GO"
            report["cause"] = "bucket_missing"
            _print(report)
            return 3
    except SupabaseStorageError as exc:
        report["steps"]["list_buckets"] = {
            "ok": False,
            "classification": exc.classification,
            "status_code": exc.status_code,
            "error_code": exc.error_code,
            "message": str(exc)[:240],
        }
        report["status"] = "NO_GO"
        report["cause"] = exc.classification or "list_buckets_failed"
        _print(report)
        return 4

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = f"diagnostics/vault-test-{ts}.pdf"

    # 2) Upload
    try:
        client.upload_object(
            bucket=bucket,
            path=path,
            content=MINIMAL_PDF,
            content_type="application/pdf",
            upsert=False,
        )
        report["steps"]["upload"] = {"ok": True, "path": path, "size": len(MINIMAL_PDF)}
    except SupabaseStorageError as exc:
        report["steps"]["upload"] = {
            "ok": False,
            "path": path,
            "classification": exc.classification,
            "status_code": exc.status_code,
            "error_code": exc.error_code,
            "endpoint": exc.endpoint,
            "message": str(exc)[:240],
        }
        report["status"] = "NO_GO"
        report["cause"] = exc.classification or "upload_failed"
        _print(report)
        return 5

    # 3) Signed URL
    try:
        signed = client.create_signed_url(bucket=bucket, path=path, expires_in=60)
        report["steps"]["signed_url"] = {
            "ok": True,
            "url_startswith_http": signed.startswith("http"),
            "url_len": len(signed),
        }
    except SupabaseStorageError as exc:
        report["steps"]["signed_url"] = {
            "ok": False,
            "classification": exc.classification,
            "status_code": exc.status_code,
            "error_code": exc.error_code,
            "message": str(exc)[:240],
        }

    # 4) Download
    try:
        downloaded = client.download_object(bucket=bucket, path=path)
        report["steps"]["download"] = {
            "ok": True,
            "size": len(downloaded),
            "matches_upload": downloaded == MINIMAL_PDF,
            "starts_with_pdf": downloaded.startswith(b"%PDF"),
        }
    except SupabaseStorageError as exc:
        report["steps"]["download"] = {
            "ok": False,
            "classification": exc.classification,
            "status_code": exc.status_code,
            "error_code": exc.error_code,
            "message": str(exc)[:240],
        }

    # 5) Delete diagnostic object
    try:
        client.delete_object(bucket=bucket, path=path)
        report["steps"]["delete"] = {"ok": True, "path": path}
    except SupabaseStorageError as exc:
        report["steps"]["delete"] = {
            "ok": False,
            "classification": exc.classification,
            "status_code": exc.status_code,
            "error_code": exc.error_code,
            "message": str(exc)[:240],
        }

    upload_ok = report["steps"].get("upload", {}).get("ok")
    download_ok = report["steps"].get("download", {}).get("ok")
    report["status"] = "GO" if upload_ok and download_ok else "NO_GO"
    _print(report)
    return 0 if report["status"] == "GO" else 6


if __name__ == "__main__":
    raise SystemExit(main())
