from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class FirebaseAuthError(Exception):
    def __init__(self, message: str = "Jeton Firebase invalide"):
        self.message = message
        super().__init__(message)


async def verify_id_token(id_token: str) -> dict[str, Any]:
    """Vérifie un ID token Firebase via Identity Toolkit (sans service account)."""
    api_key = settings.firebase_web_api_key.strip()
    if not api_key:
        raise FirebaseAuthError(
            "Firebase non configuré côté serveur. Ajoutez FIREBASE_WEB_API_KEY dans backend/.env"
        )

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={api_key}"
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(url, json={"idToken": id_token})
    except httpx.HTTPError as exc:
        logger.warning("Firebase lookup network error: %s", exc)
        raise FirebaseAuthError("Impossible de joindre Firebase Authentication") from exc

    data = response.json()
    if response.status_code >= 400:
        err = data.get("error", {}).get("message", "INVALID_ID_TOKEN")
        raise FirebaseAuthError(f"Authentification Firebase refusée ({err})")

    users = data.get("users") or []
    if not users:
        raise FirebaseAuthError("Compte Firebase introuvable")

    user = users[0]
    email = (user.get("email") or "").lower().strip()
    local_id = user.get("localId") or ""
    if not email or not local_id:
        raise FirebaseAuthError("Profil Firebase incomplet")

    if settings.firebase_project_id:
        # sanity : localId alone is enough; project check optional
        pass

    return {
        "uid": local_id,
        "email": email,
        "email_verified": bool(user.get("emailVerified")),
        "display_name": user.get("displayName") or "",
    }
