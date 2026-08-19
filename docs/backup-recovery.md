# Backup & recovery — ELFIS Core

## Backup (manuel / provider)

| Composant | Méthode | Notes |
|-----------|---------|-------|
| PostgreSQL | `pg_dump` / snapshot | quotidien recommandé |
| Vault storage | versioning bucket | hors secrets |
| Secrets | secret manager | rotation séparée |

**Pas d’exécution backup depuis une route HTTP.**

## Recovery

Voir scénarios dans `GET /api/platform/reliability/backup-policy` (`recovery`).

Ordre type : DB → config/secrets → Vault → workers → réconciliation Billing/Usage → reindex Search → smoke tests.

## Compromission secret

1. Rotation JWT / Stripe / Supabase / Brevo  
2. Redémarrage API/workers  
3. Audit `elfis_security_events` + admin audit  
4. Invalider sessions utilisateurs si nécessaire
