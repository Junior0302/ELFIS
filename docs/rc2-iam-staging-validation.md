# Rapport RC2.2 — Validation staging IAM plateforme

Date : `2026-07-22T14:46:03.953452+00:00`
Statut : **PASS**

- Environnement : `staging`
- Hôte masqué : `db.***abase.co`
- URL masquée : `postgresql+psycopg://postgres:***@db.stckzlalxrupgawgrojk.supabase.co:5432/postgres`

## Tables

- requises : `elfis_platform_roles, elfis_platform_permissions, elfis_platform_role_permissions, elfis_platform_user_roles`
- manquantes : `[]`

## Sync / bootstrap

```json
{
  "sync": {
    "created": 44,
    "updated": 0,
    "unchanged": 0,
    "inactivated": 0,
    "catalog_size": 44
  },
  "bootstrap": {
    "roles_created": 5,
    "roles_updated": 0,
    "user_assignments": 0
  }
}
```

- Rôles système : `['platform_admin', 'platform_operator', 'platform_support', 'platform_viewer', 'super_admin']`
- Assignments actives (préexistantes, non modifiées) : `0`

## Erreurs

- aucune

## Secrets

- DATABASE_URL complète non exposée
- aucun secret détecté dans le rapport

Aucun commit. Aucun push. Aucune attribution utilisateur automatique.
