# ELFIS Reliability V1

## Rétention

`RetentionService` charge les durées depuis l’environnement.  
**Documents métier jamais auto-supprimés.**

## Cleanup

Jobs :

- `reliability.cleanup_expired_records.v1`
- `reliability.check_system_health.v1`
- `reliability.detect_stale_jobs.v1`
- `reliability.detect_stale_events.v1`

Par défaut : `ELFIS_CLEANUP_ENABLED=false`, `ELFIS_CLEANUP_DRY_RUN=true`.

## Stale jobs / events

Détection + incident Platform Admin dédupliqué. **Pas** de fail/republish automatique.

## Backup / Recovery

Politiques documentées (`backup_policy`, `recovery_policy`).  
Aucune route n’exécute `pg_dump`. RPO/RTO cibles V1 : 24h / 8h (à valider ops).

## Shutdown

`run_shutdown()` arrête l’acceptation de nouveaux jobs et exécute les hooks.
