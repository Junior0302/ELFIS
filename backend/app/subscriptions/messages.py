from __future__ import annotations

from app.subscriptions.constants import PRICE_AMOUNT_CENTS, UX_STATUS_LABELS


def format_user_message(status: str, *, date: str | None = None, reason: str | None = None) -> str:
    if status == "none":
        return (
            "Votre compte est actif, mais aucun abonnement ComptaPilot IA n’est associé à ce compte."
        )
    if status == "checkout_pending":
        return (
            "Votre souscription n’est pas encore finalisée. "
            "Aucun prélèvement actif n’a été confirmé."
        )
    if status == "trialing":
        return (
            f"Votre essai gratuit ComptaPilot IA est actif jusqu’au {date or '—'}."
        )
    if status == "cancel_scheduled":
        return (
            "Votre abonnement a été résilié. "
            f"Vous conservez l’accès jusqu’au {date or '—'}."
        )
    if status in {"canceled", "expired"}:
        return (
            f"Votre abonnement ComptaPilot IA n’est plus actif depuis le {date or '—'}. "
            "Vos données sont conservées, mais les fonctionnalités premium sont désactivées."
        )
    if status == "past_due":
        return (
            "Nous n’avons pas pu renouveler votre abonnement. "
            f"Veuillez mettre à jour votre moyen de paiement avant le {date or '—'}."
        )
    if status == "admin_revoked":
        return (
            "L’accès à votre abonnement a été suspendu par l’administration. "
            f"Motif : {reason or 'non précisé'}."
        )
    return UX_STATUS_LABELS.get(status, status)


def trial_disclosure(trial_end: str | None) -> str:
    end = trial_end or "la fin de l’essai"
    euros = PRICE_AMOUNT_CENTS / 100
    return (
        f"À la fin de votre essai, votre abonnement sera automatiquement renouvelé "
        f"au tarif de {euros:.0f} € par mois, sauf annulation avant le {end}."
    )
