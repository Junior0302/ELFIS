# Runbook — Restauration base de données

## Objectif
Restaurer PostgreSQL après incident, avec validation avant bascule.

## RPO / RTO
Voir `database-backup.md` — **décisions business obligatoires** avant production.

## Prérequis
- Backup vérifié (`verify_backup.py`)
- Fenêtre d’incident déclarée
- Base **temporaire** distincte de la production pour validation
- Confirmation explicite humaine pour toute cible non test/staging

## Garde-fou script
```bash
python backend/scripts/production/verify_restore.py \
  --target-database-url "$TEMP_DATABASE_URL" \
  --backup-path "$BACKUP_FILE"
```
Refuse les URL `prod`/`production`/`live` sans marqueur test/staging.

## Procédure

1. **Déclarer l’incident** (canal ops + ticket).
2. **Stopper les écritures** (maintenance API, scale workers à 0).
3. **Sélectionner le backup** (date, checksum, taille).
4. **Restaurer dans une base temporaire**
   ```bash
   createdb elfis_restore_tmp
   pg_restore -d "$TEMP_DATABASE_URL" --clean --if-exists "$BACKUP_FILE"
   ```
5. **Vérifier l’intégrité** — counts orgs/users/documents/subscriptions/jobs/events/audits.
6. **Appliquer migrations SQL manquantes** si le backup est antérieur.
7. **Smoke tests** contre une API pointant temporairement sur la base restore (staging).
8. **Basculer** DNS/connexion prod uniquement après validation.
9. **Relancer workers** ; vérifier claim jobs/events.
10. **Documenter** la perte éventuelle (écart RPO).

## Résultat attendu
- ready ok
- pas de comptes recette en production
- idempotence webhooks préservée

## Rollback de la restore
Conserver l’ancienne volume/snapshot jusqu’à confirmation + N heures.

## Ne jamais
- `pg_restore` direct sur la prod sans restore temporaire validé
- Lancer `verify_restore` / restore sur URL distante sans confirmation
