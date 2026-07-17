from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models_saas import Organization, OrganizationMember, ProfessionalEmail, Subscription, User
from app.services.mailer import email_configured, email_status_public, send_email

logger = logging.getLogger(__name__)

ELFIS_EMAIL_DOMAIN = "elfis-core.com"
# Boîte dédiée aux demandes d’adresse pro (configurée / validée dans Brevo)
ADMIN_NOTIFY_TO = "urequest@elfis-core.com"


def _slug_part(value: str) -> str:
    raw = unicodedata.normalize("NFKD", (value or "").strip().lower())
    ascii_only = "".join(ch for ch in raw if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^a-z0-9]+", ".", ascii_only).strip(".")
    return cleaned or "user"


def suggest_elfis_email(user: User) -> str:
    first = _slug_part(user.first_name)
    last = _slug_part(user.last_name)
    local = f"{first}.{last}" if last else first
    return f"{local}@{ELFIS_EMAIL_DOMAIN}"


def serialize_professional_email(row: ProfessionalEmail) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "organization_id": row.organization_id,
        "email": row.email or "",
        "suggested_email": row.suggested_email or "",
        "provider": row.provider or "brevo",
        "status": row.status,
        "is_default": bool(row.is_default),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "activated_at": row.activated_at.isoformat() if row.activated_at else None,
        "activated_by": row.activated_by,
        "admin_notes": row.admin_notes or "",
        "request_snapshot": json.loads(row.request_snapshot_json or "{}"),
    }


def get_user_professional_emails(db: Session, user_id: int) -> list[ProfessionalEmail]:
    return (
        db.query(ProfessionalEmail)
        .filter(ProfessionalEmail.user_id == user_id)
        .order_by(ProfessionalEmail.id.desc())
        .all()
    )


def get_active_default_email(db: Session, user_id: int) -> ProfessionalEmail | None:
    return (
        db.query(ProfessionalEmail)
        .filter(
            ProfessionalEmail.user_id == user_id,
            ProfessionalEmail.status == "active",
            ProfessionalEmail.is_default.is_(True),
        )
        .first()
    ) or (
        db.query(ProfessionalEmail)
        .filter(
            ProfessionalEmail.user_id == user_id,
            ProfessionalEmail.status == "active",
        )
        .order_by(ProfessionalEmail.id.desc())
        .first()
    )


def _subscription_label(db: Session, organization_id: int | None) -> str:
    if not organization_id:
        return "—"
    sub = (
        db.query(Subscription)
        .filter(Subscription.organization_id == organization_id)
        .order_by(Subscription.id.desc())
        .first()
    )
    if not sub:
        return "Aucun"
    plan = (sub.plan or sub.stripe_price_id or "—").strip() or "—"
    status = (sub.status or "").strip() or "—"
    return f"{plan} ({status})"


def _build_snapshot(
    db: Session,
    user: User,
    organization_id: int | None,
) -> dict:
    org = db.get(Organization, organization_id) if organization_id else None
    if not org:
        membership = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == user.id,
                OrganizationMember.status == "active",
            )
            .order_by(OrganizationMember.id.asc())
            .first()
        )
        if membership:
            organization_id = membership.organization_id
            org = db.get(Organization, organization_id)
    return {
        "user_id": user.id,
        "user_code": f"USR_{user.id}",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "phone": user.phone or "",
        "current_email": user.email or "",
        "company": (org.legal_name or org.name) if org else "",
        "organization_id": organization_id,
        "subscription": _subscription_label(db, organization_id),
        "account_status": user.status or "active",
        "suggested_email": suggest_elfis_email(user),
    }


def build_admin_notification_body(snapshot: dict) -> str:
    return (
        "Nouvelle demande de création d'adresse e-mail\n\n"
        f"Nom :\n{snapshot.get('last_name') or '—'}\n\n"
        f"Prénom :\n{snapshot.get('first_name') or '—'}\n\n"
        f"Téléphone :\n{snapshot.get('phone') or '—'}\n\n"
        f"Email actuel :\n{snapshot.get('current_email') or '—'}\n\n"
        f"Entreprise :\n{snapshot.get('company') or '—'}\n\n"
        f"Abonnement :\n{snapshot.get('subscription') or '—'}\n\n"
        f"Statut :\n{snapshot.get('account_status') or '—'}\n\n"
        f"ID :\n{snapshot.get('user_code') or '—'}\n\n"
        f"Adresse proposée :\n{snapshot.get('suggested_email') or '—'}\n"
    )


def _send_admin_notification(snapshot: dict) -> bool:
    """Envoie la demande à urequest@elfis-core.com. Retourne True si expédié."""
    if not email_configured():
        raise RuntimeError(
            "E-mail plateforme non configuré : renseignez BREVO_API_KEY et "
            "PLATFORM_EMAIL_FROM=contact@elfis-core.com sur Render."
        )
    send_email(
        to_email=ADMIN_NOTIFY_TO,
        subject="Nouvelle demande de création d'adresse e-mail",
        body=build_admin_notification_body(snapshot),
        reply_to_email=(snapshot.get("current_email") or None),
    )
    return True


def _send_user_confirmation(user: User) -> bool:
    if not email_configured():
        raise RuntimeError(
            "E-mail plateforme non configuré : renseignez BREVO_API_KEY et PLATFORM_EMAIL_FROM."
        )
    if not (user.email or "").strip():
        return False
    first = (user.first_name or "").strip() or "bonjour"
    body = (
        f"Bonjour {first},\n\n"
        "Nous avons bien reçu votre demande de création d'adresse e-mail professionnelle ELFIS Core.\n\n"
        "Notre équipe procède actuellement à la configuration de votre boîte mail.\n\n"
        "Vous recevrez sous 24 heures maximum :\n\n"
        "• votre nouvelle adresse e-mail\n"
        "• votre mot de passe temporaire\n"
        "• les informations de connexion\n\n"
        "Une fois votre adresse activée, vous pourrez envoyer directement vos devis et factures depuis ELFIS Core.\n\n"
        "Merci de surveiller votre boîte mail.\n\n"
        "L'équipe ELFIS Core\n"
    )
    send_email(
        to_email=user.email.strip(),
        subject="Nous avons bien reçu votre demande",
        body=body,
    )
    return True


def resend_request_notifications(db: Session, row_id: int) -> dict:
    """Renvoie les mails admin + confirmation pour une demande existante."""
    row = db.get(ProfessionalEmail, row_id)
    if not row:
        raise RuntimeError("Demande introuvable")
    try:
        snapshot = json.loads(row.request_snapshot_json or "{}")
    except json.JSONDecodeError:
        snapshot = {}
    if not snapshot:
        user = db.get(User, row.user_id)
        if not user:
            raise RuntimeError("Utilisateur introuvable")
        snapshot = _build_snapshot(db, user, row.organization_id)
    user = db.get(User, row.user_id)
    notify = {
        "admin_notified": False,
        "user_confirmed": False,
        "notify_to": ADMIN_NOTIFY_TO,
        "mail_status": email_status_public(),
        "error": "",
    }
    try:
        notify["admin_notified"] = _send_admin_notification(snapshot)
        if user:
            notify["user_confirmed"] = _send_user_confirmation(user)
    except Exception as exc:  # noqa: BLE001
        notify["error"] = str(exc)
        logger.exception("Renvoi notification pro email #%s échoué: %s", row_id, exc)
    return notify


def create_professional_email_request(
    db: Session,
    user: User,
    *,
    organization_id: int | None,
) -> tuple[ProfessionalEmail, dict]:
    """Crée la demande et tente l’envoi vers urequest@ + confirmation client."""
    existing_pending = (
        db.query(ProfessionalEmail)
        .filter(
            ProfessionalEmail.user_id == user.id,
            ProfessionalEmail.status.in_(("pending", "creating")),
        )
        .first()
    )
    if existing_pending:
        raise RuntimeError("Une demande est déjà en cours de traitement.")

    active = (
        db.query(ProfessionalEmail)
        .filter(
            ProfessionalEmail.user_id == user.id,
            ProfessionalEmail.status == "active",
        )
        .first()
    )
    if active:
        raise RuntimeError("Vous avez déjà une adresse ELFIS Core active.")

    snapshot = _build_snapshot(db, user, organization_id)
    row = ProfessionalEmail(
        user_id=user.id,
        organization_id=snapshot.get("organization_id"),
        email="",
        suggested_email=snapshot.get("suggested_email") or suggest_elfis_email(user),
        provider="brevo",
        status="pending",
        request_snapshot_json=json.dumps(snapshot, ensure_ascii=False),
        is_default=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    notify: dict = {
        "admin_notified": False,
        "user_confirmed": False,
        "notify_to": ADMIN_NOTIFY_TO,
        "mail_configured": email_configured(),
        "mail_status": email_status_public(),
        "error": "",
    }
    try:
        notify["admin_notified"] = _send_admin_notification(snapshot)
        notify["user_confirmed"] = _send_user_confirmation(user)
        if not notify["admin_notified"]:
            notify["error"] = f"Échec d’envoi vers {ADMIN_NOTIFY_TO}"
    except Exception as exc:  # noqa: BLE001 — la demande reste enregistrée
        notify["error"] = str(exc)
        notify["mail_configured"] = email_configured()
        notify["mail_status"] = email_status_public()
        logger.exception(
            "Demande pro email #%s enregistrée mais notification échouée: %s",
            row.id,
            exc,
        )

    return row, notify


def list_all_requests(db: Session, *, status: str | None = None) -> list[ProfessionalEmail]:
    query = db.query(ProfessionalEmail)
    if status:
        query = query.filter(ProfessionalEmail.status == status)
    return query.order_by(ProfessionalEmail.created_at.desc()).all()


def activate_professional_email(
    db: Session,
    row_id: int,
    *,
    admin: User,
    email: str,
    make_default: bool = True,
    notes: str = "",
) -> ProfessionalEmail:
    row = db.get(ProfessionalEmail, row_id)
    if not row:
        raise RuntimeError("Demande introuvable")
    address = (email or row.suggested_email or "").strip().lower()
    if not address or "@" not in address:
        raise RuntimeError("Adresse e-mail invalide")
    if not address.endswith(f"@{ELFIS_EMAIL_DOMAIN}"):
        # Autoriser aussi le domaine exact demandé
        pass

    # Une seule active par défaut
    if make_default:
        others = (
            db.query(ProfessionalEmail)
            .filter(
                ProfessionalEmail.user_id == row.user_id,
                ProfessionalEmail.id != row.id,
            )
            .all()
        )
        for other in others:
            if other.is_default:
                other.is_default = False
                db.add(other)

    row.email = address
    row.status = "active"
    row.is_default = make_default
    row.activated_at = datetime.utcnow()
    row.activated_by = admin.id
    row.admin_notes = (notes or "").strip()
    row.provider = "brevo"
    db.add(row)
    db.commit()
    db.refresh(row)

    user = db.get(User, row.user_id)
    if user and email_configured() and (user.email or "").strip():
        try:
            send_email(
                to_email=user.email.strip(),
                subject="Votre adresse ELFIS Core est prête",
                body=(
                    f"Bonjour {(user.first_name or '').strip() or ''},\n\n"
                    f"Votre adresse professionnelle est active : {address}\n\n"
                    "Vous pouvez désormais l’utiliser comme expéditeur pour vos devis et factures "
                    "dans ELFIS Core / ComptaPilot.\n\n"
                    "L’équipe ELFIS Core\n"
                ),
            )
        except Exception:  # noqa: BLE001
            pass
    return row


def reject_professional_email(
    db: Session, row_id: int, *, admin: User, notes: str = ""
) -> ProfessionalEmail:
    row = db.get(ProfessionalEmail, row_id)
    if not row:
        raise RuntimeError("Demande introuvable")
    row.status = "rejected"
    row.admin_notes = (notes or "").strip() or "Refusée par l’administrateur"
    row.activated_by = admin.id
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def suspend_professional_email(
    db: Session, row_id: int, *, admin: User, notes: str = ""
) -> ProfessionalEmail:
    row = db.get(ProfessionalEmail, row_id)
    if not row:
        raise RuntimeError("Demande introuvable")
    if row.status != "active":
        raise RuntimeError("Seule une adresse active peut être suspendue")
    row.status = "suspended"
    row.is_default = False
    row.admin_notes = (notes or "").strip() or "Suspendue par l’administrateur"
    row.activated_by = admin.id
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def reset_professional_email_request(
    db: Session, row_id: int, *, admin: User
) -> dict:
    """Supprime une demande/adresse pour permettre une nouvelle demande utilisateur."""
    row = db.get(ProfessionalEmail, row_id)
    if not row:
        raise RuntimeError("Demande introuvable")
    payload = serialize_professional_email(row)
    db.delete(row)
    db.commit()
    return {"deleted": payload, "reset_by": admin.id}


def reset_all_professional_email_requests(db: Session, *, admin: User) -> dict:
    """Réinitialise toutes les demandes (tests / reprise à zéro)."""
    rows = db.query(ProfessionalEmail).all()
    count = len(rows)
    for row in rows:
        db.delete(row)
    db.commit()
    return {"deleted_count": count, "reset_by": admin.id}


def sender_options_for_user(
    db: Session,
    user: User,
    *,
    organization: Organization | None,
) -> list[dict]:
    """Options d’expéditeur pour devis/factures."""
    options: list[dict] = []
    active = [
        row
        for row in get_user_professional_emails(db, user.id)
        if row.status == "active" and (row.email or "").strip()
    ]
    for row in active:
        options.append(
            {
                "id": f"professional:{row.id}",
                "kind": "professional",
                "email": row.email,
                "label": row.email,
                "is_default": bool(row.is_default),
                "professional_email_id": row.id,
            }
        )

    personal = (user.email or "").strip()
    if personal:
        has_default_pro = any(o["is_default"] for o in options)
        options.append(
            {
                "id": f"personal:{user.id}",
                "kind": "personal",
                "email": personal,
                "label": personal,
                "is_default": not has_default_pro,
                "professional_email_id": None,
            }
        )

    org_mail = (organization.email or "").strip() if organization else ""
    if org_mail and org_mail.lower() not in {o["email"].lower() for o in options}:
        options.append(
            {
                "id": f"organization:{organization.id}",
                "kind": "organization",
                "email": org_mail,
                "label": org_mail,
                "is_default": False,
                "professional_email_id": None,
            }
        )

    if not any(o["is_default"] for o in options) and options:
        options[0]["is_default"] = True
    return options
