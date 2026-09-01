"""State HMAC anti-CSRF pour le retour Bridge Connect.

Le navigateur ne fournit jamais un item_id « nu » : le callback exige un state
signé lié à l’organisation et à la tentative de connexion.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

from app.config import settings

_STATE_TTL_SECONDS = 20 * 60


class ConsentStateError(Exception):
    pass


def _secret() -> bytes:
    return (settings.jwt_secret or "").encode("utf-8")


def issue_consent_state(
    *,
    organization_id: int,
    connection_id: int,
    purpose: str = "connect",
) -> str:
    kind = (purpose or "connect").strip() or "connect"
    if kind not in {"connect", "reauth"}:
        kind = "connect"
    payload = {
        "o": int(organization_id),
        "c": int(connection_id),
        "e": int(time.time()) + _STATE_TTL_SECONDS,
        "p": kind,
        "n": hashlib.sha256(f"{organization_id}:{connection_id}:{time.time_ns()}".encode()).hexdigest()[:16],
    }
    body = urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")
    sig = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_consent_state(state: str) -> dict[str, int]:
    raw = (state or "").strip()
    if "." not in raw:
        raise ConsentStateError("State de consentement invalide.")
    body, sig = raw.rsplit(".", 1)
    expected = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise ConsentStateError("State de consentement invalide.")
    try:
        payload = json.loads(urlsafe_b64decode(body.encode("ascii")))
    except Exception as exc:
        raise ConsentStateError("State de consentement invalide.") from exc
    try:
        org_id = int(payload["o"])
        connection_id = int(payload["c"])
        expires = int(payload["e"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ConsentStateError("State de consentement invalide.") from exc
    if expires < int(time.time()):
        raise ConsentStateError("State de consentement expiré.")
    purpose = str(payload.get("p") or "connect").strip() or "connect"
    if purpose not in {"connect", "reauth"}:
        purpose = "connect"
    return {"organization_id": org_id, "connection_id": connection_id, "purpose": purpose}
