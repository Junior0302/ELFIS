from __future__ import annotations

from datetime import datetime
from typing import Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models_saas import OrganizationMember, Subscription, SubscriptionNotification, User
from app.subscriptions.messages import trial_disclosure


TEMPLATES: dict[str, Callable[..., tuple[str, str]]] = {}


def _register(name: str):
    def deco(fn):
        TEMPLATES[name] = fn
        return fn

    return deco


@_register("welcome_no_subscription")
def _welcome(first_name: str, **_) -> tuple[str, str]:
    return (
        "Bienvenue sur ComptaPilot IA",
        (
            f"Bonjour {first_name},\n\n"
            "Votre compte ComptaPilot IA a bien été créé.\n\n"
            "Aucun abonnement n’est encore actif. Vous pouvez démarrer votre essai gratuit "
            "de 14 jours depuis votre espace Abonnement et facturation.\n\n"
            "L’équipe ComptaPilot IA\n"
        ),
    )


@_register("trial_started")
def _trial_started(first_name: str, trial_end: str | None = None, **_) -> tuple[str, str]:
    return (
        "Votre essai gratuit ComptaPilot IA est actif",
        (
            f"Bonjour {first_name},\n\n"
            f"Votre essai gratuit de 14 jours a commencé.\n\n"
            f"{trial_disclosure(trial_end)}\n\n"
            "Aucun prélèvement n’est effectué aujourd’hui.\n\n"
            "L’équipe ComptaPilot IA\n"
        ),
    )


@_register("trial_ending")
def _trial_ending(first_name: str, trial_end: str | None = None, **_) -> tuple[str, str]:
    return (
        "Votre essai ComptaPilot IA se termine bientôt",
        (
            f"Bonjour {first_name},\n\n"
            f"Votre essai gratuit se terminera le {trial_end or '—'}.\n\n"
            "À cette date, votre abonnement sera automatiquement renouvelé au tarif de 19 € par mois.\n\n"
            "L’équipe ComptaPilot IA\n"
        ),
    )


@_register("payment_succeeded")
def _payment_ok(first_name: str, next_billing: str | None = None, **_) -> tuple[str, str]:
    return (
        "Paiement confirmé — ComptaPilot IA",
        (
            f"Bonjour {first_name},\n\n"
            "Le paiement de votre abonnement ComptaPilot IA a été confirmé.\n"
            f"Prochaine échéance : {next_billing or '—'}\n\n"
            "L’équipe ComptaPilot IA\n"
        ),
    )


@_register("payment_failed")
def _payment_fail(first_name: str, grace_until: str | None = None, **_) -> tuple[str, str]:
    return (
        "Action requise pour votre abonnement ComptaPilot IA",
        (
            f"Bonjour {first_name},\n\n"
            "Le paiement de votre abonnement n’a pas pu être effectué.\n"
            f"Veuillez mettre à jour votre moyen de paiement avant le {grace_until or '—'}.\n\n"
            "L’équipe ComptaPilot IA\n"
        ),
    )


@_register("cancel_scheduled")
def _cancel(first_name: str, access_ends: str | None = None, **_) -> tuple[str, str]:
    return (
        "Confirmation de résiliation de votre abonnement",
        (
            f"Bonjour {first_name},\n\n"
            "Votre demande de résiliation a bien été enregistrée.\n"
            f"Vous conservez l’accès jusqu’au {access_ends or '—'}.\n\n"
            "L’équipe ComptaPilot IA\n"
        ),
    )


@_register("subscription_ended")
def _ended(first_name: str, ended_at: str | None = None, **_) -> tuple[str, str]:
    return (
        "Votre abonnement ComptaPilot IA est terminé",
        (
            f"Bonjour {first_name},\n\n"
            f"Votre abonnement a pris fin le {ended_at or '—'}.\n"
            "Les fonctionnalités premium sont désactivées. Vos données ne sont pas supprimées.\n\n"
            "L’équipe ComptaPilot IA\n"
        ),
    )


@_register("admin_revoked")
def _revoked(first_name: str, reason: str | None = None, **_) -> tuple[str, str]:
    return (
        "Modification de votre accès ComptaPilot IA",
        (
            f"Bonjour {first_name},\n\n"
            "Votre accès a été interrompu par l’administration.\n"
            f"Motif : {reason or 'non précisé'}\n\n"
            "L’équipe ComptaPilot IA\n"
        ),
    )


def _smtp_ready() -> bool:
    from app.services.mailer import email_configured

    return email_configured()


def _send_email(recipient: str, subject: str, body: str) -> str:
    from app.services.mailer import send_email

    send_email(to_email=recipient, subject=subject, body=body)
    return f"mail:{recipient}"


def enqueue_notification(
    db: Session,
    *,
    organization_id: int,
    notification_type: str,
    deduplication_key: str,
    user_id: int | None = None,
    subscription_id: int | None = None,
    recipient: str = "",
    channel: str = "email",
    template_kwargs: dict | None = None,
) -> SubscriptionNotification | None:
    existing = (
        db.query(SubscriptionNotification)
        .filter(SubscriptionNotification.deduplication_key == deduplication_key)
        .first()
    )
    if existing:
        return existing

    note = SubscriptionNotification(
        user_id=user_id,
        organization_id=organization_id,
        subscription_id=subscription_id,
        notification_type=notification_type,
        channel=channel,
        recipient=recipient,
        status="pending",
        deduplication_key=deduplication_key,
        scheduled_at=datetime.utcnow(),
    )
    db.add(note)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return (
            db.query(SubscriptionNotification)
            .filter(SubscriptionNotification.deduplication_key == deduplication_key)
            .first()
        )

    if channel == "email" and recipient and notification_type in TEMPLATES:
        first_name = "client"
        if user_id:
            user = db.get(User, user_id)
            if user:
                first_name = user.first_name or user.email.split("@")[0]
        subject, body = TEMPLATES[notification_type](first_name=first_name, **(template_kwargs or {}))
        try:
            msg_id = _send_email(recipient, subject, body)
            note.status = "sent"
            note.sent_at = datetime.utcnow()
            note.provider_message_id = msg_id
        except Exception as exc:  # noqa: BLE001 — journaliser l’échec sans casser le flux
            note.status = "failed"
            note.failed_at = datetime.utcnow()
            note.failure_reason = str(exc)[:500]
        db.add(note)
    elif channel == "in_app":
        note.status = "sent"
        note.sent_at = datetime.utcnow()
        db.add(note)
    return note


def notify_org_owners(
    db: Session,
    *,
    organization_id: int,
    notification_type: str,
    subscription: Subscription | None,
    suffix: str,
    template_kwargs: dict | None = None,
) -> int:
    members = (
        db.query(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.status == "active",
        )
        .all()
    )
    sent = 0
    for member, user in members:
        role_name = getattr(member, "role_id", None)
        # Notifier tous les membres actifs (owners inclus via permission côté produit)
        key = f"{notification_type}:{organization_id}:{user.id}:{suffix}"
        note = enqueue_notification(
            db,
            organization_id=organization_id,
            notification_type=notification_type,
            deduplication_key=key,
            user_id=user.id,
            subscription_id=subscription.id if subscription else None,
            recipient=user.email,
            channel="email",
            template_kwargs=template_kwargs,
        )
        if note and note.status == "sent":
            sent += 1
        # silence unused
        _ = role_name
    return sent


def run_trial_reminders(db: Session, *, days_before: int) -> int:
    """Rappels J-N avant fin d’essai (idempotent via deduplication_key)."""
    now = datetime.utcnow()
    rows = (
        db.query(Subscription)
        .filter(Subscription.status == "trialing", Subscription.trial_end.isnot(None))
        .all()
    )
    count = 0
    for row in rows:
        if not row.trial_end:
            continue
        delta = (row.trial_end - now).total_seconds()
        window = days_before * 86400
        if delta < 0 or delta > window + 86400:
            continue
        day_key = row.trial_end.date().isoformat()
        count += notify_org_owners(
            db,
            organization_id=row.organization_id,
            notification_type="trial_ending",
            subscription=row,
            suffix=f"j{days_before}:{day_key}",
            template_kwargs={"trial_end": row.trial_end.isoformat()},
        )
    return count
