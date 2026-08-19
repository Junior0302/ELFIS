# Politique de rétention Audit Engine (RC2.3 étape 3)

## Variables d’environnement

| Variable | Défaut | Rôle |
|----------|--------|------|
| `AUDIT_RETENTION_DAYS` | 365 | Défaut |
| `AUDIT_SECURITY_RETENTION_DAYS` | 730 | Catégorie SECURITY |
| `AUDIT_AUTH_RETENTION_DAYS` | 365 | Catégorie AUTH |
| `AUDIT_CRITICAL_RETENTION_DAYS` | 1095 | Sévérité CRITICAL |
| `AUDIT_ARCHIVE_BATCH_SIZE` | 1000 | Taille de lot |

La durée effective d’un événement = **maximum** des politiques applicables (CRITICAL et SECURITY se cumulent pour allonger la conservation).

## Archivage

- Table : `elfis_audit_events_archive`
- Copie puis suppression de la table live
- Idempotent (déjà archivé → retrait live)
- Batch + SAVEPOINT par ligne
- Aucune purge automatique au démarrage
- Aucune tâche cron installée dans cette étape

## Commandes

```bash
set ELFIS_ENVIRONMENT=staging
python -m scripts.audit.retention --preview

python -m scripts.audit.retention --archive --confirm --batch-size 500

python -m scripts.audit.retention --purge-archive --confirm
```

`--preview` est le comportement sûr. Toute écriture exige `--confirm`.  
Environnement obligatoire (`ELFIS_ENVIRONMENT` / `APP_ENV`).

## Permissions

| Permission | Usage |
|------------|--------|
| `security.audit.retention.read` | Lecture politique / preview (API future) |
| `security.audit.retention.manage` | Archivage / purge (CLI ; super_admin) |

`platform_admin` : retention.read, **pas** retention.manage.  
`platform_operator` / `viewer` : lecture audit seulement.

## Limites

- Pas de purge automatique
- Pas d’UI d’archivage dans Activity Center
- Purge archive optionnelle et explicite uniquement
- Pas de restauration UI (restauration = réinsertion manuelle depuis archive)
