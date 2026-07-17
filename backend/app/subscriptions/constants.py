from __future__ import annotations

PLAN_COMPTAPILOT_MONTHLY = "comptapilot_monthly"
TERMS_VERSION_DEFAULT = "v1"
PRICE_AMOUNT_CENTS = 1900
CURRENCY = "EUR"

PLANS = {
    PLAN_COMPTAPILOT_MONTHLY: {
        "name": "ComptaPilot IA",
        "price_amount": PRICE_AMOUNT_CENTS,
        "currency": CURRENCY,
        "billing_interval": "month",
        "trial_days": 14,
        "features": {
            "ai_accounting_assistant": True,
            "invoice_analysis": True,
            "financial_validation": True,
            "accounting_mapping": True,
            "anomaly_detection": True,
            "invoice_management": True,
            "quote_management": True,
            "dashboard_access": True,
            "exports": True,
            "history_access": True,
            "crm_clients": True,
            "crm_catalog": True,
            "crm_activities": True,
        },
        "limits": {
            "documents_per_month": None,
            "ai_requests_per_month": None,
            "storage_mb": None,
        },
        "feature_labels": [
            "Analyse intelligente de documents comptables",
            "Extraction des informations de factures et justificatifs",
            "Contrôle de cohérence des montants",
            "Détection d’anomalies",
            "Classement comptable assisté",
            "Préparation d’écritures comptables",
            "Assistance comptable par intelligence artificielle",
            "Gestion des factures et devis",
            "Clients, catalogue et activités commerciales",
            "Tableaux de bord et historique",
            "Exports disponibles",
        ],
    }
}

ACCESS_RAW_STATUSES = {"active", "trialing"}
PRO_PLAN_STATUSES = {"trialing", "active", "past_due", "unpaid", "paused"}

UX_STATUS_LABELS = {
    "none": "Aucun abonnement",
    "checkout_pending": "Souscription non finalisée",
    "trialing": "Essai gratuit",
    "active": "Abonnement actif",
    "past_due": "Paiement à régulariser",
    "unpaid": "Impayé",
    "paused": "Suspendu",
    "cancel_scheduled": "Résiliation programmée",
    "canceled": "Abonnement terminé",
    "expired": "Abonnement expiré",
    "admin_revoked": "Accès suspendu",
    "incomplete": "Paiement incomplet",
    "incomplete_expired": "Paiement expiré",
}

ERROR_CODES = {
    "SUBSCRIPTION_REQUIRED": "Cette fonctionnalité nécessite un abonnement ComptaPilot IA actif.",
    "TRIAL_EXPIRED": "Votre essai gratuit est terminé.",
    "PAYMENT_REQUIRED": "Une mise à jour du moyen de paiement est requise.",
    "SUBSCRIPTION_CANCELED": "Votre abonnement n’est plus actif.",
    "SUBSCRIPTION_SUSPENDED": "L’accès a été suspendu par l’administration.",
    "FEATURE_NOT_INCLUDED": "Cette fonctionnalité n’est pas incluse dans votre offre.",
    "USAGE_LIMIT_REACHED": "La limite d’utilisation a été atteinte.",
    "ACCOUNT_DISABLED": "Ce compte est désactivé.",
    "TRIAL_ALREADY_USED": "L’essai gratuit a déjà été utilisé pour cette organisation.",
    "CHECKOUT_ALREADY_PENDING": "Une session de paiement est déjà en cours.",
    "SUBSCRIPTION_ALREADY_ACTIVE": "Un abonnement actif existe déjà.",
}
