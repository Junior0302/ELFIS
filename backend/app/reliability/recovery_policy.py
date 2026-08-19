"""Politique de reprise après incident — documentée, non automatique."""

from __future__ import annotations

from typing import Any


def recovery_policy() -> dict[str, Any]:
    return {
        "version": "v1",
        "automatic": False,
        "targets": {
            "rpo_hours": 24,
            "rto_hours": 8,
            "notes": "Cibles V1 indicatives — à valider opérationnellement.",
        },
        "scenarios": [
            {
                "id": "db_loss",
                "title": "Perte base de données",
                "steps": [
                    "Restaurer dernier dump/snapshot Postgres",
                    "Vérifier migrations / tables critiques",
                    "Réconcilier Billing (Stripe) et Usage",
                    "Relancer workers jobs/events",
                ],
            },
            {
                "id": "vault_loss",
                "title": "Perte stockage Vault",
                "steps": [
                    "Restaurer bucket Supabase/storage",
                    "Vérifier métadonnées DB vs objets",
                    "Ne pas supprimer les lignes documents orphelines sans audit",
                ],
            },
            {
                "id": "worker_down",
                "title": "Worker arrêté",
                "steps": [
                    "Redémarrer processus worker",
                    "Inspecter jobs/events stale",
                    "Créer incidents si dead letters massives",
                ],
            },
            {
                "id": "stripe_down",
                "title": "Stripe indisponible",
                "steps": [
                    "Mode dégradé lecture",
                    "File d'attente webhooks / retry Stripe",
                    "Réconciliation post-incident",
                ],
            },
            {
                "id": "openai_down",
                "title": "OpenAI indisponible",
                "steps": [
                    "Jobs AI en retry/backoff",
                    "Pas de faux succès",
                    "Incidents si taux d'erreur élevé",
                ],
            },
            {
                "id": "email_down",
                "title": "Fournisseur e-mail indisponible",
                "steps": [
                    "Delivery retries",
                    "Alertes Delivery failed agrégées",
                ],
            },
            {
                "id": "search_corrupt",
                "title": "Index Search corrompu",
                "steps": [
                    "Job reindex organization / global",
                    "Vérifier zero-results anormal",
                ],
            },
            {
                "id": "migration_failed",
                "title": "Migration échouée",
                "steps": [
                    "Ne pas démarrer en ready",
                    "Rollback schema si possible",
                    "Appliquer SQL documenté manuellement",
                ],
            },
            {
                "id": "secret_compromised",
                "title": "Secret compromis",
                "steps": [
                    "Rotation JWT / Stripe / Supabase / Brevo",
                    "Invalider sessions si possible",
                    "Audit security events",
                ],
            },
        ],
        "post_restore_checks": [
            "GET /health/ready == ok",
            "platform admin health services",
            "sample vault download",
            "billing subscription sync sample",
            "search query smoke",
        ],
    }
