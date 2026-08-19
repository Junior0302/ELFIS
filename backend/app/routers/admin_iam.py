"""API admin minimale — rôles IAM plateforme."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.iam.permission_catalog import Permission
from app.iam.permission_context import PermissionContext
from app.iam.permission_dependencies import require_any_permission, require_permission
from app.iam.platform_role_service import PlatformRoleService
from app.models_saas import User

router = APIRouter(prefix="/admin/iam", tags=["admin-iam"])


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    description: str | None = None
    is_system: bool
    is_active: bool


class UserRoleOut(BaseModel):
    role_id: str
    code: str
    name: str
    is_system: bool
    assigned_at: str | None = None
    expires_at: str | None = None


class UserPermissionsOut(BaseModel):
    user_id: int
    permissions: list[str] = Field(default_factory=list)
    # Pas de détails secrets ; liste triée des codes uniquement


class AssignRoleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expires_at: str | None = None  # ISO8601 optionnel — parsing simple côté service si besoin


def _svc(db: Session = Depends(get_db)) -> PlatformRoleService:
    return PlatformRoleService(db)


@router.get("/roles", response_model=list[RoleOut])
def list_roles(
    _ctx: PermissionContext = Depends(
        require_any_permission(
            Permission.SECURITY_PERMISSIONS_READ.value,
            Permission.SECURITY_PERMISSIONS_MANAGE.value,
        )
    ),
    svc: PlatformRoleService = Depends(_svc),
) -> list[RoleOut]:
    return [RoleOut.model_validate(r) for r in svc.list_roles()]


@router.get("/roles/{role_id}", response_model=RoleOut)
def get_role(
    role_id: str,
    _ctx: PermissionContext = Depends(
        require_any_permission(
            Permission.SECURITY_PERMISSIONS_READ.value,
            Permission.SECURITY_PERMISSIONS_MANAGE.value,
        )
    ),
    svc: PlatformRoleService = Depends(_svc),
) -> RoleOut:
    role = svc.get_role(role_id)
    if not role:
        raise HTTPException(404, detail={"code": "role_not_found", "message": "Rôle introuvable"})
    return RoleOut.model_validate(role)


@router.get("/users/{user_id}/roles", response_model=list[UserRoleOut])
def list_user_roles(
    user_id: int,
    _ctx: PermissionContext = Depends(
        require_any_permission(
            Permission.SECURITY_PERMISSIONS_READ.value,
            Permission.SECURITY_PERMISSIONS_MANAGE.value,
        )
    ),
    svc: PlatformRoleService = Depends(_svc),
    db: Session = Depends(get_db),
) -> list[UserRoleOut]:
    if not db.get(User, user_id):
        raise HTTPException(404, detail={"code": "user_not_found", "message": "Utilisateur introuvable"})
    return [UserRoleOut(**r) for r in svc.list_user_roles(user_id)]


@router.get("/users/{user_id}/permissions", response_model=UserPermissionsOut)
def list_user_permissions(
    user_id: int,
    _ctx: PermissionContext = Depends(
        require_any_permission(
            Permission.SECURITY_PERMISSIONS_READ.value,
            Permission.SECURITY_PERMISSIONS_MANAGE.value,
        )
    ),
    svc: PlatformRoleService = Depends(_svc),
    db: Session = Depends(get_db),
) -> UserPermissionsOut:
    if not db.get(User, user_id):
        raise HTTPException(404, detail={"code": "user_not_found", "message": "Utilisateur introuvable"})
    # Permissions effectives IAM persistantes uniquement (+ cache)
    # La compatibilité is_platform_admin n'est pas listée ici pour éviter confusion ;
    # le resolver live la fusionne à la requête.
    perms = sorted(svc.effective_permissions_for_user(user_id))
    return UserPermissionsOut(user_id=user_id, permissions=perms)


@router.post("/users/{user_id}/roles/{role_id}", status_code=204, response_class=Response)
def assign_role(
    user_id: int,
    role_id: str,
    ctx: PermissionContext = Depends(
        require_permission(Permission.SECURITY_PERMISSIONS_MANAGE.value)
    ),
    svc: PlatformRoleService = Depends(_svc),
) -> Response:
    role = svc.get_role(role_id)
    if not role:
        raise HTTPException(404, detail={"code": "role_not_found", "message": "Rôle introuvable"})
    try:
        svc.assign_role_to_user(
            user_id,
            role.code,
            actor_user_id=ctx.user_id,
        )
    except ValueError as exc:
        code = str(exc)
        status = 404 if "not_found" in code else 400
        raise HTTPException(status, detail={"code": code, "message": "Opération refusée"}) from exc
    return Response(status_code=204)


@router.delete("/users/{user_id}/roles/{role_id}", status_code=204, response_class=Response)
def revoke_role(
    user_id: int,
    role_id: str,
    ctx: PermissionContext = Depends(
        require_permission(Permission.SECURITY_PERMISSIONS_MANAGE.value)
    ),
    svc: PlatformRoleService = Depends(_svc),
) -> Response:
    role = svc.get_role(role_id)
    if not role:
        raise HTTPException(404, detail={"code": "role_not_found", "message": "Rôle introuvable"})
    try:
        svc.revoke_role_from_user(user_id, role.code, actor_user_id=ctx.user_id)
    except ValueError as exc:
        code = str(exc)
        status = 404 if "not_found" in code else 400
        raise HTTPException(status, detail={"code": code, "message": "Opération refusée"}) from exc
    return Response(status_code=204)
