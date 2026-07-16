from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.models_saas import (
    AIAgent,
    Organization,
    OrganizationMember,
    Permission,
    Role,
    User,
    AuditLog,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLE_PERMS: dict[str, list[str]] = {
    "owner": ["*"],
    "admin": [
        "users.invite",
        "users.manage",
        "settings.manage",
        "documents.read",
        "documents.write",
        "invoice.create",
        "invoice.delete",
        "invoice.read",
        "bank.read",
        "bank.connect",
        "tax.manage",
        "ai.analysis",
        "finance.read",
        "subscription.manage",
    ],
    "cfo": [
        "finance.read",
        "bank.read",
        "ai.analysis",
        "forecast.read",
        "reporting.read",
        "invoice.read",
        "tax.manage",
    ],
    "comptable": [
        "invoice.create",
        "invoice.read",
        "invoice.delete",
        "tax.manage",
        "bank.read",
        "documents.read",
        "documents.write",
    ],
    "employe": ["invoice.create", "documents.read", "quote.create"],
    "auditeur": ["invoice.read", "documents.read", "finance.read", "bank.read", "tax.read"],
}

ALL_PERMISSIONS = [
    ("invoice.create", "facturation"),
    ("invoice.delete", "facturation"),
    ("invoice.read", "facturation"),
    ("quote.create", "facturation"),
    ("bank.read", "banque"),
    ("bank.connect", "banque"),
    ("tax.manage", "fiscalite"),
    ("tax.read", "fiscalite"),
    ("users.invite", "auth"),
    ("users.manage", "auth"),
    ("settings.manage", "settings"),
    ("documents.read", "documents"),
    ("documents.write", "documents"),
    ("ai.analysis", "analyse-ia"),
    ("finance.read", "finance"),
    ("forecast.read", "previsions"),
    ("reporting.read", "pilotage"),
    ("subscription.manage", "subscription"),
]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(data: dict[str, Any], expires_minutes: int = 60 * 24 * 7) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError:
        return None


def ensure_rbac_catalog(db: Session) -> dict[str, Role]:
    """Crée rôles / permissions s'ils manquent (sans comptes démo)."""
    for name, module in ALL_PERMISSIONS:
        if not db.query(Permission).filter(Permission.name == name).first():
            db.add(Permission(name=name, module=module, description=name))

    roles: dict[str, Role] = {}
    for role_name, perms in ROLE_PERMS.items():
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(
                name=role_name,
                permissions=json.dumps(perms),
                description=role_name.title(),
            )
            db.add(role)
            db.flush()
        else:
            role.permissions = json.dumps(perms)
            db.add(role)
        roles[role_name] = role
    db.commit()
    return roles


def seed_auth(db: Session) -> None:
    """Catalogue RBAC uniquement — comptes via Firebase /register."""
    ensure_rbac_catalog(db)
    for user in db.query(User).all():
        should_be_admin = user.email.lower() in settings.platform_admin_email_set
        if user.is_platform_admin != should_be_admin:
            user.is_platform_admin = should_be_admin
            db.add(user)
    # Les anciens agents de roadmap n'étaient pas reliés à un service réel.
    db.query(AIAgent).filter(AIAgent.type != "finance").delete(synchronize_session=False)
    # Retire d'anciens comptes fictifs s'ils existent encore
    for email in ("jean.dupont@katuku.com", "marie.martin@katuku.com"):
        user = db.query(User).filter(User.email == email).first()
        if not user:
            continue
        db.query(OrganizationMember).filter(OrganizationMember.user_id == user.id).delete()
        db.query(AuditLog).filter(AuditLog.user_id == user.id).delete()
        db.delete(user)
    db.commit()


def upsert_firebase_user(
    db: Session,
    *,
    firebase_uid: str,
    email: str,
    first_name: str = "",
    last_name: str = "",
    organization_name: str | None = None,
) -> User:
    roles = ensure_rbac_catalog(db)
    owner_role = roles["owner"]

    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if not user:
        user = db.query(User).filter(User.email == email).first()

    if user:
        user.firebase_uid = firebase_uid
        user.email = email
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.last_login = datetime.utcnow()
        user.is_platform_admin = email.lower() in settings.platform_admin_email_set
        db.add(user)
        db.flush()
    else:
        display = email.split("@")[0]
        user = User(
            first_name=first_name or display.title(),
            last_name=last_name or "",
            email=email,
            password_hash="",
            firebase_uid=firebase_uid,
            status="active",
            is_platform_admin=email.lower() in settings.platform_admin_email_set,
            last_login=datetime.utcnow(),
        )
        db.add(user)
        db.flush()

        org_name = (organization_name or f"{user.first_name} {user.last_name}".strip() or "Mon entreprise").strip()
        org = Organization(
            name=org_name,
            legal_name=org_name,
            subscription_plan="starter",
        )
        db.add(org)
        db.flush()
        db.add(
            OrganizationMember(
                user_id=user.id,
                organization_id=org.id,
                role_id=owner_role.id,
                status="active",
            )
        )
        db.add(
            AIAgent(
                organization_id=org.id,
                name="Finance Agent",
                type="finance",
                model=settings.openai_chat_model,
                status="active",
            )
        )

    db.commit()
    db.refresh(user)
    return user


def get_user_memberships(db: Session, user_id: int) -> list[dict]:
    from app.services.plan_features import org_effective_plan

    rows = (
        db.query(OrganizationMember, Organization, Role)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .join(Role, Role.id == OrganizationMember.role_id)
        .filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == "active",
        )
        .all()
    )
    result = []
    for member, org, role in rows:
        plan, sub_status = org_effective_plan(db, org.id)
        result.append(
            {
                "membership_id": member.id,
                "organization_id": org.id,
                "organization_name": org.name,
                "organization_logo": org.logo or "",
                "role": role.name,
                "status": member.status,
                "permissions": json.loads(role.permissions or "[]"),
                "plan": plan,
                "subscription_status": sub_status,
                "country": org.country,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            }
        )
    return result


def user_has_permission(permissions: list[str], required: str) -> bool:
    if "*" in permissions:
        return True
    return required in permissions


def write_audit(
    db: Session,
    *,
    user_id: int | None,
    organization_id: int | None,
    action: str,
    module: str,
    ip: str = "",
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            organization_id=organization_id,
            action=action,
            module=module,
            ip=ip,
        )
    )
    db.commit()
