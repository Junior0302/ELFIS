# Rapport RC2.3 étape 2 — Activity Center / API lecture

Date : `2026-07-22T15:16:11.039761+00:00`
Statut : **PASS**

- Environnement : `staging`
- Hôte masqué : `db.***abase.co`
- URL masquée : `postgresql+psycopg://postgres:***@db.stckzlalxrupgawgrojk.supabase.co:5432/postgres`
- Route frontend : `/elfadmin/activity`
- Routes API audit : `['/api/admin/audit/events', '/api/admin/audit/events/{event_id}', '/api/admin/audit/statistics']`
- Routes totales : `264`

## Probe

```json
{
  "event_id": "88cc6deb-4133-4641-9c67-2d14998ae2cd",
  "action": "LOGIN_FAILURE",
  "metadata_keys": [
    "probe",
    "reason"
  ],
  "page_items": 1,
  "total_24h": 1,
  "stats_keys": [
    "by_action",
    "by_category",
    "by_severity",
    "failure",
    "hours",
    "iam_changes",
    "login_failure",
    "permission_denied",
    "since",
    "success",
    "total",
    "warnings_errors"
  ],
  "login_failure": 1,
  "permission_denied": 0
}
```

- Probe supprimé : `True`

## Erreurs

- `[]`

## Secrets

- DATABASE_URL non exposée en clair
- métadonnées password absentes du probe

Aucun commit. Aucun push.
