from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


PREFIX = "v1:"


def _fernet() -> Fernet:
    raw = (settings.email_credentials_encryption_key or "").strip()
    if not raw:
        # Dev fallback dérivé du JWT secret (jamais en prod sans clé dédiée)
        if settings.app_env.lower() == "production":
            raise RuntimeError("EMAIL_CREDENTIALS_ENCRYPTION_KEY manquante")
        digest = hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()
        raw = base64.urlsafe_b64encode(digest).decode("ascii")
    try:
        return Fernet(raw.encode("ascii") if isinstance(raw, str) else raw)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("EMAIL_CREDENTIALS_ENCRYPTION_KEY invalide") from exc


def encrypt_secret(plaintext: str) -> str:
    value = (plaintext or "").strip()
    if not value:
        return ""
    token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{PREFIX}{token}"


def decrypt_secret(ciphertext: str) -> str:
    raw = (ciphertext or "").strip()
    if not raw:
        return ""
    if raw.startswith(PREFIX):
        raw = raw[len(PREFIX) :]
    try:
        return _fernet().decrypt(raw.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Impossible de déchiffrer le secret e-mail") from exc


def encryption_ready() -> bool:
    try:
        _fernet()
        return True
    except Exception:  # noqa: BLE001
        return False
