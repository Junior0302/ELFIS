# ELFIS Admin — Abonnements

## Accès

Réservé aux comptes `is_platform_admin` / emails `PLATFORM_ADMIN_EMAILS`.  
UI : `/elfadmin/abonnements`.

## Actions disponibles

| Action | Endpoint | Effet |
|--------|----------|--------|
| Sync Stripe | `POST /platform/organizations/{id}/subscriptions/sync` | Recharge l’abo depuis Stripe |
| Révoquer | `.../revoke` | `admin_revoked_*` + notification |
| Restaurer | `.../restore` | lève la suspension interne |
| Grant essai | `.../grant-trial` | `trial_eligibility_status=admin_granted` |
| Orphelins | `GET /platform/subscriptions/orphans` | abo Stripe sans org |
| Résumé IA | `POST /platform/subscriptions/ai-summary` | lecture seule + suggestions |

Toute action sensible écrit une entrée d’audit (`write_audit`).

## Règles

- Le motif public de révocation est visible client ; la note interne ne l’est pas.
- L’IA admin **ne exécute jamais** d’action : confirmation humaine obligatoire.
- Ne pas modifier un statut Stripe uniquement en base : utiliser Sync.
