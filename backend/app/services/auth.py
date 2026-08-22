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
        "email_accounts.manage",
        "email_accounts.view",
        "documents.read",
        "documents.write",
        "documents.create",
        "documents.download",
        "documents.archive",
        "documents.send_email",
        "documents.view_email_history",
        "invoice.create",
        "invoice.delete",
        "invoice.read",
        "bank.read",
        "bank.connect",
        "tax.manage",
        "ai.analysis",
        "finance.read",
        "subscription.manage",
        "sales.read",
        "sales.write",
        "sales.manage",
        "sales.pipeline.manage",
        "sales.export",
        "sales.admin",
        "sales.proposals.read",
        "sales.proposals.write",
        "sales.proposals.approve",
        "sales.proposals.send",
        "sales.proposals.accept",
        "sales.proposals.convert",
        "sales.proposals.delete",
        "sales.proposals.admin",
        "sales.intelligence.read",
        "sales.intelligence.manage",
        "sales.intelligence.dismiss",
        "sales.intelligence.sync",
        "sales.team.read",
        "sales.team.manage",
        "sales.assign",
        "sales.review",
        "sales.comment",
        "sales.mention",
        "sales.transfer",
        "accounting.view",
        "accounting.edit",
        "accounting.validate",
        "accounting.reject",
        "accounting.reopen",
    ],
    "cfo": [
        "finance.read",
        "bank.read",
        "ai.analysis",
        "forecast.read",
        "reporting.read",
        "invoice.read",
        "tax.manage",
        "documents.read",
        "documents.download",
        "documents.send_email",
        "documents.view_email_history",
        "email_accounts.view",
        "sales.read",
        "sales.export",
        "sales.proposals.read",
        "sales.intelligence.read",
        "sales.team.read",
        "sales.comment",
    ],
    "comptable": [
        "invoice.create",
        "invoice.read",
        "invoice.delete",
        "tax.manage",
        "bank.read",
        "documents.read",
        "documents.write",
        "documents.create",
        "documents.download",
        "documents.archive",
        "documents.send_email",
        "documents.view_email_history",
        "email_accounts.view",
        "sales.read",
        "sales.proposals.read",
        "sales.comment",
        "accounting.view",
        "accounting.edit",
        "accounting.validate",
        "accounting.reject",
        "accounting.reopen",
    ],
    "employe": [
        "invoice.create",
        "documents.read",
        "documents.write",
        "documents.create",
        "documents.download",
        "quote.create",
        "documents.send_email",
        "sales.read",
        "sales.write",
        "sales.proposals.read",
        "sales.proposals.write",
        "sales.proposals.send",
        "sales.proposals.accept",
        "sales.intelligence.read",
        "sales.intelligence.dismiss",
        "sales.team.read",
        "sales.assign",
        "sales.review",
        "sales.comment",
        "sales.mention",
        "sales.transfer",
    ],
    "auditeur": [
        "invoice.read",
        "documents.read",
        "documents.download",
        "documents.view_email_history",
        "finance.read",
        "bank.read",
        "tax.read",
        "sales.read",
        "sales.proposals.read",
        "sales.intelligence.read",
        "sales.team.read",
    ],
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
    ("documents.create", "documents"),
    ("documents.download", "documents"),
    ("documents.archive", "documents"),
    ("documents.send_email", "documents"),
    ("documents.view_email_history", "documents"),
    ("email_accounts.view", "email"),
    ("email_accounts.manage", "email"),
    ("ai.analysis", "analyse-ia"),
    ("finance.read", "finance"),
    ("forecast.read", "previsions"),
    ("reporting.read", "pilotage"),
    ("subscription.manage", "subscription"),
    ("sales.read", "sales"),
    ("sales.write", "sales"),
    ("sales.manage", "sales"),
    ("sales.pipeline.manage", "sales"),
    ("sales.export", "sales"),
    ("sales.admin", "sales"),
    ("sales.proposals.read", "sales"),
    ("sales.proposals.write", "sales"),
    ("sales.proposals.approve", "sales"),
    ("sales.proposals.send", "sales"),
    ("sales.proposals.accept", "sales"),
    ("sales.proposals.convert", "sales"),
    ("sales.proposals.delete", "sales"),
    ("sales.proposals.admin", "sales"),
    ("sales.intelligence.read", "sales"),
    ("sales.intelligence.manage", "sales"),
    ("sales.intelligence.dismiss", "sales"),
    ("sales.intelligence.sync", "sales"),
    ("sales.team.read", "sales"),
    ("sales.team.manage", "sales"),
    ("sales.assign", "sales"),
    ("sales.review", "sales"),
    ("sales.comment", "sales"),
    ("sales.mention", "sales"),
    ("sales.transfer", "sales"),
    ("accounting.view", "accounting"),
    ("accounting.edit", "accounting"),
    ("accounting.validate", "accounting"),
    ("accounting.reject", "accounting"),
    ("accounting.reopen", "accounting"),
]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(data: dict[str, Any], expires_minutes: int = 60 * 24 * 7) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
    issuer = (getattr(settings, "elfis_jwt_issuer", "") or "").strip()
    audience = (getattr(settings, "elfis_jwt_audience", "") or "").strip()
    if issuer:
        payload["iss"] = issuer
    if audience:
        payload["aud"] = audience
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        kwargs: dict[str, Any] = {
            "algorithms": ["HS256"],
        }
        issuer = (getattr(settings, "elfis_jwt_issuer", "") or "").strip()
        audience = (getattr(settings, "elfis_jwt_audience", "") or "").strip()
        enforce = bool(getattr(settings, "elfis_jwt_enforce_issuer_audience", False))
        if enforce and issuer:
            kwargs["issuer"] = issuer
        if enforce and audience:
            kwargs["audience"] = audience
        options: dict[str, Any] = {}
        if not enforce:
            options["verify_aud"] = False
        # python-jose : pas de kwarg leeway — tolérance via options si supportée
        skew = int(getattr(settings, "elfis_jwt_clock_skew_seconds", 30) or 0)
        if skew > 0:
            options["leeway"] = skew
        if options:
            kwargs["options"] = options
        return jwt.decode(token, settings.jwt_secret, **kwargs)
    except JWTError:
        return None
    except TypeError:
        # Fallback si options.leeway non supporté
        try:
            return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], options={"verify_aud": False})
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
