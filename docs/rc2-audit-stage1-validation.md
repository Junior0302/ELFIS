# Rapport RC2.3 — Validation staging Audit Engine

Date : `2026-07-22T15:05:31.062850+00:00`
Statut : **PASS**

- Environnement : `staging`
- Hôte masqué : `db.***abase.co`
- URL masquée : `postgresql+psycopg://postgres:***@db.stckzlalxrupgawgrojk.supabase.co:5432/postgres`

## Tables

- requises : `{'required': ['elfis_audit_events'], 'missing': []}`

## Index

- `{'required': ['ix_elfis_audit_events_occurred_at', 'ix_elfis_audit_events_action', 'ix_elfis_audit_events_actor_user_id', 'ix_elfis_audit_events_correlation_id'], 'missing': []}`

## Probe

```json
{
  "event_id": "b24f3dc0-a0d1-4eef-b86f-5df8fa2398eb",
  "action": "LOGIN_SUCCESS",
  "metadata_keys": [
    "probe"
  ]
}
```

- Routes audit : `['/api/admin/audit/events', '/api/admin/audit/events/{event_id}', '/api/admin/audit/statistics']`
- Routes totales : `264`

## Erreurs

- `[]`

## Secrets

- DATABASE_URL complète non exposée
- aucun secret attendu dans le rapport

Aucun commit. Aucun push.
