from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models_saas import User
from app.services.auth import decode_token, get_user_memberships, user_has_permission


class AuthContext:
    def __init__(
        self,
        user: User | None,
        organization_id: int | None,
        role: str | None,
        permissions: list[str],
    ):
        self.user = user
        self.organization_id = organization_id
        self.role = role
        self.permissions = permissions

    def require(self, permission: str) -> None:
        if self.user is None:
            raise HTTPException(401, detail="Authentification requise")
        if not user_has_permission(self.permissions, permission):
            raise HTTPException(403, detail=f"Permission refusée: {permission}")


def get_auth_context(
    authorization: str | None = Header(default=None),
    x_organization_id: int | None = Header(default=None, alias="X-Organization-Id"),
    db: Session = Depends(get_db),
) -> AuthContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        if settings.auth_required:
            raise HTTPException(401, detail="Authentification requise")
        return AuthContext(None, x_organization_id, None, ["*"])

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(401, detail="Token invalide")

    user = db.get(User, int(payload["sub"]))
    if not user or user.status != "active":
        raise HTTPException(401, detail="Utilisateur inactif")

    memberships = get_user_memberships(db, user.id)
    if not memberships:
        raise HTTPException(403, detail="Aucune organisation")

    org_id = x_organization_id or int(payload.get("org_id") or memberships[0]["organization_id"])
    current = next((m for m in memberships if m["organization_id"] == org_id), None)
    if not current:
        raise HTTPException(403, detail="Accès organisation refusé")

    return AuthContext(user, org_id, current["role"], current["permissions"])
