# Runbook — Rollback

## Objectif
Revenir à un état stable après un déploiement défectueux.

## Types

### A. Rollback applicatif (sans migration destructive)
1. Redéployer le tag précédent API + workers **de la même génération de schéma**.
2. Vérifier `/api/health/ready`.
3. Smoke read-only.
4. Surveiller jobs/events pending (payloads `.v1` doivent rester compatibles).

### B. Roll-forward (correction)
1. Corriger le bug sur une branche hotfix.
2. Tests Phase G / non-régression ciblés.
3. Déployer le hotfix (préférable si migration déjà appliquée).

### C. Migration incompatible
1. **Ne pas** `alembic downgrade` (Alembic absent ; downgrades SQL souvent irréversibles).
2. Restaurer la base depuis backup pré-migration sur environnement temporaire.
3. Valider intégrité puis bascule contrôlée (voir `database-restore.md`).
4. Redéployer l’ancienne version applicative compatible.

### D. Incident provider (Stripe / AI / mail / storage)
1. Désactiver le flag module concerné si disponible.
2. Mode dégradé documenté ; API reste ready si dépendance optionnelle.
3. Pas de rollback code sauf si le bug est applicatif.

### E. Incident base
1. Stop écritures (maintenance / scale-to-zero writers).
2. Restore selon runbook.
3. Relancer workers après ready.

## Contrôles post-rollback
- ready ok
- pas d’augmentation jobs failed
- webhooks Stripe non rejoués en double (idempotence event_id)
- frontend cache éventuel : hard refresh / purge CDN si applicable

## Compatibilité
| Élément | Règle |
|---------|-------|
| Schéma | Version app N compatible schéma N et N-1 si migrations expand-only |
| Workers | Éviter 2 versions incompatibles sur le même type de job |
| Events | Champs optionnels only ; rupture → `.v2` |
| Frontend | Aligner sur API déployée |

## Ne jamais
- Downgrade SQL en production sans restore testé
- Supprimer des données pour « débloquer »
