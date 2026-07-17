from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models_saas import (
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    Role,
    TeamNotification,
    User,
)
from app.services.auth import ensure_rbac_catalog, write_audit
from app.services.plan_features import can_invite_more

INVITE_TTL_DAYS = 14
MANAGEABLE_ROLES = {"admin", "cfo", "comptable", "employe", "auditeur"}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _notify(
    db: Session,
    *,
    user_id: int,
    organization_id: int | None,
    kind: str,
    title: str,
    body: str,
    payload: dict | None = None,
) -> None:
    db.add(
        TeamNotification(
            user_id=user_id,
            organization_id=organization_id,
            kind=kind,
            title=title,
            body=body,
            payload_json=json.dumps(payload or {}, ensure_ascii=False),
        )
    )


def _send_invite_email(*, to_email: str, org_name: str, role: str, accept_url: str) -> str | None:
    """Envoie l'e-mail si le transport est configuré. Retourne None ou message d'erreur."""
    from app.services.mailer import email_configured, send_email

    if not email_configured():
        return "E-mail non configuré — invitation créée, lien à transmettre manuellement."
    body = (
        f"Bonjour,\n\nVous êtes invité(e) à rejoindre l’organisation « {org_name} » "
        f"sur ComptaPilot IA avec le rôle « {role} ».\n\n"
        f"Accepter l’invitation :\n{accept_url}\n\n"
        f"Ce lien expire dans {INVITE_TTL_DAYS} jours.\n\n"
        "Si vous n’avez pas encore de compte, créez-en un avec cette adresse e-mail "
        "puis acceptez l’invitation depuis Mon compte.\n\n"
        "Cordialement,\nComptaPilot IA\n"
    )
    try:
        send_email(
            to_email=to_email,
            subject=f"Invitation à rejoindre {org_name} sur ComptaPilot",
            body=body,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        return str(exc)[:300]


def create_invitation(
    db: Session,
    *,
    organization_id: int,
    email: str,
    role: str,
    invited_by: int,
) -> tuple[OrganizationInvitation, str, str | None]:
    """
    Crée une invitation. Retourne (invitation, raw_token, email_warning).
    """
    email_norm = email.strip().lower()
    role_name = role.strip().lower()
    if role_name not in MANAGEABLE_ROLES:
        raise ValueError("Rôle non autorisé")
    if not email_norm or "@" not in email_norm:
        raise ValueError("Adresse e-mail invalide")

    ok, reason = can_invite_more(db, organization_id)
    if not ok:
        raise ValueError(reason)

    org = db.get(Organization, organization_id)
    if not org:
        raise ValueError("Organisation introuvable")

    existing_user = db.query(User).filter(User.email == email_norm).first()
    if existing_user:
        membership = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == existing_user.id,
                OrganizationMember.status.in_(("active", "suspended")),
            )
            .first()
        )
        if membership:
            raise ValueError("Cet utilisateur appartient déjà à l’organisation")

    pending = (
        db.query(OrganizationInvitation)
        .filter(
            OrganizationInvitation.organization_id == organization_id,
            OrganizationInvitation.email == email_norm,
            OrganizationInvitation.status == "pending",
        )
        .first()
    )
    if pending:
        if pending.expires_at and pending.expires_at < datetime.utcnow():
            pending.status = "expired"
            db.add(pending)
        else:
            raise ValueError("Une invitation est déjà en attente pour cette adresse")

    raw = secrets.token_urlsafe(32)
    invite = OrganizationInvitation(
        organization_id=organization_id,
        email=email_norm,
        role=role_name,
        permissions_json="[]",
        token_hash=_hash_token(raw),
        status="pending",
        invited_by=invited_by,
        expires_at=datetime.utcnow() + timedelta(days=INVITE_TTL_DAYS),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    accept_url = f"{settings.frontend_url.rstrip('/')}/compte?invite={raw}"
    mail_warn = _send_invite_email(
        to_email=email_norm, org_name=org.name, role=role_name, accept_url=accept_url
    )

    if existing_user:
        _notify(
            db,
            user_id=existing_user.id,
            organization_id=organization_id,
            kind="invitation_received",
            title=f"Invitation : {org.name}",
            body=f"Vous êtes invité(e) à rejoindre {org.name} en tant que {role_name}.",
            payload={"invitation_id": invite.id, "organization_id": organization_id},
        )
        db.commit()

    write_audit(
        db,
        user_id=invited_by,
        organization_id=organization_id,
        action=f"invitation.create:{email_norm}:{role_name}",
        module="auth",
    )
    return invite, raw, mail_warn


def get_invitation_by_token(db: Session, token: str) -> OrganizationInvitation | None:
    if not token:
        return None
    invite = (
        db.query(OrganizationInvitation)
        .filter(OrganizationInvitation.token_hash == _hash_token(token))
        .first()
    )
    if not invite:
        return None
    if invite.status == "pending" and invite.expires_at < datetime.utcnow():
        invite.status = "expired"
        db.add(invite)
        db.commit()
        db.refresh(invite)
    return invite


def list_pending_for_email(db: Session, email: str) -> list[OrganizationInvitation]:
    now = datetime.utcnow()
    rows = (
        db.query(OrganizationInvitation)
        .filter(
            OrganizationInvitation.email == email.strip().lower(),
            OrganizationInvitation.status == "pending",
        )
        .order_by(OrganizationInvitation.id.desc())
        .all()
    )
    changed = False
    for inv in rows:
        if inv.expires_at < now:
            inv.status = "expired"
            db.add(inv)
            changed = True
    if changed:
        db.commit()
    return [r for r in rows if r.status == "pending"]


def _resolve_pending_invite(
    db: Session,
    *,
    user: User,
    token: str | None = None,
    invitation_id: int | None = None,
) -> OrganizationInvitation:
    invite: OrganizationInvitation | None = None
    if token:
        invite = get_invitation_by_token(db, token)
    elif invitation_id is not None:
        invite = db.get(OrganizationInvitation, invitation_id)
        if invite and invite.status == "pending" and invite.expires_at < datetime.utcnow():
            invite.status = "expired"
            db.add(invite)
            db.commit()
            db.refresh(invite)
    if not invite or invite.status != "pending":
        raise ValueError("Invitation introuvable ou déjà traitée")
    if invite.email.lower() != (user.email or "").lower():
        raise ValueError("Cette invitation est destinée à une autre adresse e-mail")
    return invite


def accept_invitation(
    db: Session,
    *,
    user: User,
    token: str | None = None,
    invitation_id: int | None = None,
) -> OrganizationMember:
    invite = _resolve_pending_invite(db, user=user, token=token, invitation_id=invitation_id)
    roles = ensure_rbac_catalog(db)
    role = roles.get(invite.role) or roles["employe"]

    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == invite.organization_id,
            OrganizationMember.user_id == user.id,
        )
        .first()
    )
    if membership:
        if membership.status == "active":
            invite.status = "accepted"
            invite.accepted_at = datetime.utcnow()
            db.add(invite)
            db.commit()
            raise ValueError("Vous êtes déjà membre de cette organisation")
        membership.status = "active"
        membership.role_id = role.id
        membership.invited_by = invite.invited_by
        membership.joined_at = datetime.utcnow()
    else:
        membership = OrganizationMember(
            user_id=user.id,
            organization_id=invite.organization_id,
            role_id=role.id,
            status="active",
            invited_by=invite.invited_by,
        )
        db.add(membership)

    invite.status = "accepted"
    invite.accepted_at = datetime.utcnow()
    db.add(invite)
    db.commit()
    db.refresh(membership)

    org = db.get(Organization, invite.organization_id)
    if invite.invited_by:
        _notify(
            db,
            user_id=invite.invited_by,
            organization_id=invite.organization_id,
            kind="invitation_accepted",
            title="Invitation acceptée",
            body=f"{user.email} a rejoint {org.name if org else 'l’organisation'}.",
            payload={"user_id": user.id, "membership_id": membership.id},
        )
    _notify(
        db,
        user_id=user.id,
        organization_id=invite.organization_id,
        kind="organization_joined",
        title="Organisation rejointe",
        body=f"Vous êtes désormais membre de {org.name if org else 'l’organisation'}.",
        payload={"organization_id": invite.organization_id},
    )
    db.commit()
    write_audit(
        db,
        user_id=user.id,
        organization_id=invite.organization_id,
        action=f"invitation.accept:{invite.id}",
        module="auth",
    )
    return membership


def refuse_invitation(
    db: Session,
    *,
    user: User,
    token: str | None = None,
    invitation_id: int | None = None,
) -> None:
    invite = _resolve_pending_invite(db, user=user, token=token, invitation_id=invitation_id)
    invite.status = "refused"
    db.add(invite)
    db.commit()
    if invite.invited_by:
        _notify(
            db,
            user_id=invite.invited_by,
            organization_id=invite.organization_id,
            kind="invitation_refused",
            title="Invitation refusée",
            body=f"{user.email} a refusé l’invitation.",
            payload={"invitation_id": invite.id},
        )
        db.commit()
    write_audit(
        db,
        user_id=user.id,
        organization_id=invite.organization_id,
        action=f"invitation.refuse:{invite.id}",
        module="auth",
    )


def cancel_invitation(
    db: Session, *, invitation_id: int, organization_id: int, actor_id: int
) -> None:
    invite = (
        db.query(OrganizationInvitation)
        .filter(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == organization_id,
        )
        .first()
    )
    if not invite:
        raise ValueError("Invitation introuvable")
    if invite.status != "pending":
        raise ValueError("Seule une invitation en attente peut être annulée")
    invite.status = "cancelled"
    db.add(invite)
    db.commit()
    write_audit(
        db,
        user_id=actor_id,
        organization_id=organization_id,
        action=f"invitation.cancel:{invitation_id}",
        module="auth",
    )


def resend_invitation(
    db: Session, *, invitation_id: int, organization_id: int, actor_id: int
) -> tuple[OrganizationInvitation, str, str | None]:
    invite = (
        db.query(OrganizationInvitation)
        .filter(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == organization_id,
        )
        .first()
    )
    if not invite:
        raise ValueError("Invitation introuvable")
    if invite.status not in {"pending", "expired"}:
        raise ValueError("Impossible de renvoyer cette invitation")
    ok, reason = can_invite_more(db, organization_id)
    # si pending compte déjà dans seats, OK; si expired besoin de place
    if invite.status == "expired" and not ok:
        raise ValueError(reason)

    raw = secrets.token_urlsafe(32)
    invite.token_hash = _hash_token(raw)
    invite.status = "pending"
    invite.expires_at = datetime.utcnow() + timedelta(days=INVITE_TTL_DAYS)
    invite.updated_at = datetime.utcnow()
    db.add(invite)
    db.commit()
    db.refresh(invite)

    org = db.get(Organization, organization_id)
    accept_url = f"{settings.frontend_url.rstrip('/')}/compte?invite={raw}"
    warn = _send_invite_email(
        to_email=invite.email,
        org_name=org.name if org else "Organisation",
        role=invite.role,
        accept_url=accept_url,
    )
    write_audit(
        db,
        user_id=actor_id,
        organization_id=organization_id,
        action=f"invitation.resend:{invitation_id}",
        module="auth",
    )
    return invite, raw, warn


def leave_organization(db: Session, *, user: User, organization_id: int) -> None:
    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user.id,
            OrganizationMember.organization_id == organization_id,
        )
        .first()
    )
    if not membership:
        raise ValueError("Vous n’êtes pas membre de cette organisation")
    role = db.get(Role, membership.role_id)
    if role and role.name == "owner":
        raise ValueError(
            "Le propriétaire ne peut pas quitter l’organisation sans transférer la propriété."
        )
    membership.status = "removed"
    db.add(membership)
    db.commit()
    write_audit(
        db,
        user_id=user.id,
        organization_id=organization_id,
        action="member.leave",
        module="auth",
    )


def serialize_invitation(inv: OrganizationInvitation, org: Organization | None = None) -> dict:
    return {
        "id": inv.id,
        "organization_id": inv.organization_id,
        "organization_name": org.name if org else None,
        "email": inv.email,
        "role": inv.role,
        "status": inv.status,
        "invited_by": inv.invited_by,
        "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
        "accepted_at": inv.accepted_at.isoformat() if inv.accepted_at else None,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }


def list_pending_invitations_for_user(db: Session, user: User) -> list[dict]:
    rows = list_pending_for_email(db, user.email or "")
    result = []
    for inv in rows:
        org = db.get(Organization, inv.organization_id)
        result.append(serialize_invitation(inv, org))
    return result


def list_notifications(db: Session, user_id: int, *, unread_only: bool = False) -> list[TeamNotification]:
    query = db.query(TeamNotification).filter(TeamNotification.user_id == user_id)
    if unread_only:
        query = query.filter(TeamNotification.is_read.is_(False))
    return query.order_by(TeamNotification.id.desc()).limit(50).all()


def serialize_notification(note: TeamNotification) -> dict:
    return {
        "id": note.id,
        "organization_id": note.organization_id,
        "kind": note.kind,
        "title": note.title,
        "body": note.body,
        "payload": json.loads(note.payload_json or "{}"),
        "is_read": note.is_read,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }


def mark_notification_read(db: Session, *, user_id: int, notification_id: int) -> TeamNotification:
    note = (
        db.query(TeamNotification)
        .filter(TeamNotification.id == notification_id, TeamNotification.user_id == user_id)
        .first()
    )
    if not note:
        raise ValueError("Notification introuvable")
    note.is_read = True
    db.add(note)
    db.commit()
    db.refresh(note)
    return note
