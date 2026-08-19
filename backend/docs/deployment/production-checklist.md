# Checklist — Production ELFIS Core

**Go/No-Go** : toutes les cases critiques `[!]` doivent être cochées.

## Configuration `[!]`
- [ ] `ELFIS_ENVIRONMENT=production`
- [ ] PostgreSQL (pas SQLite)
- [ ] `JWT_SECRET` ≥ 32, non défaut
- [ ] `CORS_ORIGINS` liste explicite (pas `*`)
- [ ] `FRONTEND_URL` hors localhost
- [ ] Stripe live + webhook secret
- [ ] Cohérence sk_live / prices live
- [ ] AI provider réel + clé (si AI activée)
- [ ] Mailer réel configuré (pas mock)
- [ ] Storage Supabase configuré
- [ ] `PLATFORM_ADMIN_EMAILS` renseigné
- [ ] DEBUG / mocks / test mode **off**
- [ ] OpenAPI `/docs` **désactivé**
- [ ] Workers in-process **off** (processus dédiés)
- [ ] Enforcement billing/entitlements/quotas selon décision produit

## Secrets `[!]`
- [ ] Aucun secret dans le dépôt (`check_secrets.py`)
- [ ] `.env` / credentials ignorés par git
- [ ] Rotation documentée

## Base `[!]`
- [ ] Backup pré-déploiement + `verify_backup.py`
- [ ] Migrations SQL appliquées
- [ ] Index critiques présents
- [ ] Pool / SSL selon hébergeur

## Runtime `[!]`
- [ ] `validate_production_config.py` → ok
- [ ] API ready
- [ ] Workers ready
- [ ] Smoke **read-only** avec `--allow-production-readonly`
- [ ] Headers sécurité (HSTS, etc.)
- [ ] Logs sans secrets
- [ ] Alertes minimales configurées

## Décisions bloquantes
- [ ] RPO / RTO fixés
- [ ] Rate-limit multi-instance (Redis/gateway) accepté ou reporté avec risque
- [ ] Outbox transactionnelle V2 : risque accepté ou planifié
- [ ] Phase F PostgreSQL réelle exécutée
- [ ] Politique rétention / RGPD validée juridiquement (minimum)

## Go / No-Go
- [ ] **GO** signé par responsable ops
- [ ] **NO-GO** si un `[!]` manque
