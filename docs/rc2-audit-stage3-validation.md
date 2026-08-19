# Rapport RC2.3 étape 3 — recherche / rétention / export

Date : `2026-07-22T15:34:20.567194+00:00`
Statut : **PASS**

- Environnement : staging
- Hôte masqué : `db.***abase.co`
- URL masquée : `postgresql+psycopg://postgres:***@db.stckzlalxrupgawgrojk.supabase.co:5432/postgres`
- Pagination cursor : `not_introduced_offset_limit_sufficient`
- Route export présente : `True`
- Routes totales : `265`

## Index / tables

- indexes : `['ix_elfis_audit_action_occurred', 'ix_elfis_audit_actor_occurred', 'ix_elfis_audit_cat_occurred', 'ix_elfis_audit_events_action', 'ix_elfis_audit_events_actor_user_id', 'ix_elfis_audit_events_category', 'ix_elfis_audit_events_correlation_id', 'ix_elfis_audit_events_occurred_at', 'ix_elfis_audit_events_organization_id', 'ix_elfis_audit_events_product', 'ix_elfis_audit_events_request_id', 'ix_elfis_audit_events_service', 'ix_elfis_audit_events_severity', 'ix_elfis_audit_events_status', 'ix_elfis_audit_org_occurred', 'ix_elfis_audit_sev_occurred', 'ix_elfis_audit_success_occurred']`

## Recherche / stats / preview

```json
{
  "search": {
    "q_hits": 1,
    "stats_total": 1
  },
  "retention_preview": {
    "expired_count": 0,
    "sample_scanned": 0
  },
  "export": {
    "bytes": 455,
    "has_password": false,
    "validate": null
  }
}
```

- Probes supprimés : `1`

## Erreurs

- `[]`

Aucun archivage de données réelles. Aucun commit. Aucun push.
