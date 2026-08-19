# Runbook — Sauvegarde base de données

## Objectif
Produire une sauvegarde PostgreSQL vérifiable (métadonnées + restore test périodique).

## Décisions business obligatoires (si non fixées = bloquant go-live)
- **RPO** (perte de données max acceptable) : _à décider_
- **RTO** (durée max de restauration) : _à décider_
- Fréquence : recommandation initiale **quotidienne** + avant chaque déploiement
- Rétention : recommandation initiale **30 jours** + 1 mensuelle 12 mois

## Prérequis
- Accès `pg_dump` ou sauvegarde managée hébergeur
- Stockage chiffré hors dépôt git
- Compte opérateur avec droits lecture seule DB + écriture bucket backup

## Procédure logique (pg_dump)

```bash
export BACKUP_FILE="elfis_$(date -u +%Y%m%dT%H%M%SZ).dump"
pg_dump "$DATABASE_URL" -Fc -f "$BACKUP_FILE"
python backend/scripts/production/verify_backup.py --path "$BACKUP_FILE"
# Transférer vers stockage chiffré (S3/GCS/…) puis supprimer la copie locale
```

## Sauvegarde managée
Si l’hébergeur fournit snapshots / PITR :
1. Déclencher ou vérifier le snapshot
2. Noter ID, région, encryption
3. Tester restore trimestriel minimum

## Contrôles (backup ≠ commande OK)
| Contrôle | Attendu |
|----------|---------|
| Taille | > 0 (seuil `--min-bytes`) |
| Checksum | enregistré (script partial SHA-256) |
| Date | cohérente UTC |
| Version PG | notée |
| Chiffrement | at-rest activé |
| Accès | restreint ops |

## Emplacement
- **Interdit** : dépôt git, `backend/`, artefacts CI publics
- **Autorisé** : bucket privé chiffré, vault backup hébergeur

## Propriétaire
Rôle ops / platform admin (nommer un responsable).

## Ne jamais
- Committer un dump
- Stocker le dump à côté du code source non chiffré
- Considérer un backup valide sans restore test périodique
