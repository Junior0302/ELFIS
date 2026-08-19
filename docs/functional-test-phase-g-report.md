# Rapport Phase G — Production readiness, déploiement, secrets, sauvegardes, runbooks

Date : 2026-07-21  
Environnement : `ELFIS_ENVIRONMENT=test` · SQLite recette · **0 appel réseau réel**  
Commande : `python scripts/run_functional_validation.py --phase-g`  
Commit / push : **aucun**

---

## Synthèse exécutive

| Domaine | Résultat |
|---------|----------|
| Environment validation | PASS |
| Production configuration | PASS |
| Secret detection | PASS |
| Debug/test route protection | PASS |
| Authentication production | PASS |
| CORS / trusted hosts | PASS (CORS validé ; TrustedHost middleware = doc infra) |
| Security headers | PASS (suite security) |
| Logging / redaction | PASS |
| PostgreSQL configuration | PASS (règles) / migrations PG **NOT EXECUTED** |
| Database migrations | PASS (scripts SQL) / upgrade PG **SKIPPED** |
| Critical indexes | PASS (présence SQL) / PG live **SKIPPED** |
| Provider configuration | PASS (sans réseau) |
| Worker startup | PASS |
| Graceful shutdown | PASS |
| Health / readiness | PASS |
| Backup documentation | PASS |
| Restore documentation | PASS |
| Rollback documentation | PASS |
| Staging smoke safety | PASS |
| Production smoke safety | PASS |
| Monitoring / alerts | PASS (documenté) |
| Retention / data policy | PASS (documenté ; décisions juridiques ouvertes) |

```
Phase G tests................... 41 passed, 1 skipped
Regression tests............... 30 passed (security/observability/reliability)
FastAPI import................. OK (250 routes)
Frontend build................. OK
Real network calls............. 0
Known critical production risks 7
PostgreSQL migration test...... NOT EXECUTED
```

---

## 1. Matrice des environnements

| | development | test | staging | production |
|--|-------------|------|---------|------------|
| Identifiant | `ELFIS_ENVIRONMENT` / `APP_ENV` | idem | idem | `production` |
| Base | SQLite OK | SQLite/PG recette | PostgreSQL dédié | PostgreSQL **obligatoire** |
| Providers | mocks OK | mocks | Stripe test / domaines recette | réels, **mocks fatals** |
| Secrets | locaux | locaux | coffre staging | coffre prod |
| Logs | debug raisonnable | info | info | info/warn/error |
| CORS | localhost OK | test | origines staging | liste explicite, pas `*` |
| OpenAPI | `/docs` | `/docs` | acceptable | **désactivé** |
| Seed fonctionnel | OK si garde-fous | OK | contrôlé | **refusé** |
| Workers in-process | OK | OK | déconseillé | **désactivés** (processus séparés) |

Production refuse silencieusement : SQLite, mocks AI/OCR/billing, JWT faible, CORS `*`, `FRONTEND_URL` localhost, debug, seed recette.

---

## 2. Variables obligatoires (production)

| Variable | Obligatoire | Notes |
|----------|-------------|-------|
| `ELFIS_ENVIRONMENT=production` | oui | alias `APP_ENV` |
| `DATABASE_URL` (postgres) | oui | SSL selon hébergeur |
| `JWT_SECRET` ≥ 32 | oui | pas la valeur défaut |
| `CORS_ORIGINS` | oui | liste HTTPS |
| `FRONTEND_URL` | oui | hors localhost |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | oui si billing | live cohérent |
| `PLATFORM_ADMIN_EMAILS` | oui | fatal si vide |
| `OPENAI_API_KEY` | si AI on | warning sinon |
| Supabase URL + service role | storage | warning si absent |
| Firebase web/project | via `validate_production_security` | |

Voir `backend/.env.example` (aucune valeur réelle).

---

## 3–9. Validations production / secrets / routes / CORS / headers / logs

- Startup : `app/security/security_startup.py` → fatals explicites, messages sans secret.
- Secrets dépôt : `scripts/production/check_secrets.py` → OK (allowlist `fake`/`example`).
- `.gitignore` : `.env`, dumps, pem, credentials, backups, coverage.
- Routes debug/test/mint-token : absentes du routeur.
- OpenAPI désactivé si `is_production()` au chargement de `main.py`.
- Auth Bearer/Firebase ; cookies session non critiques.
- Redaction : `sanitize_error_message` (Stripe, Bearer, JWT).

---

## 10–12. Base / migrations / index

**Pas d’Alembic V1.** Schéma via `backend/sql/*.sql` + `create_all` local + index Phase F.

| Test | Résultat |
|------|----------|
| Présence scripts SQL | PASS (11/11) |
| Index Delivery conditionnel | PASS (fichier Phase F) |
| Unique webhook `provider_event_id` | PASS (SQL billing) |
| Vault checksum unique | PASS |
| Search GIN | PASS |
| `alembic upgrade` base vide | **NOT EXECUTED** (pas d’URL PG dédiée) |
| Upgrade schéma existant | **staging manuel** |

---

## 13–16. Providers / workers / health

- Import FastAPI sans réseau : PASS.
- Stripe/AI mocks refusés en prod : PASS.
- Workers : bootstrap handlers + shutdown hooks PASS.
- Prod : workers in-process désactivés dans `lifespan`.
- Live / ready : PASS (ready error si DB down).

---

## 17–20. Backup / restore / rollback / smoke

Runbooks : `backend/docs/runbooks/` (mirroir `docs/runbooks/`).  
Scripts : `verify_backup.py`, `verify_restore.py` (refuse prod destructive), `smoke_test.py` (exige `--allow-production-readonly`).

---

## 21–24. Monitoring / alertes / rétention / RGPD

### Alertes minimales (seuils ajustables)
API not ready, 5xx, latence, DB down, pool saturé, jobs/events pending/failed, payment_failed, webhooks invalides, storage/AI/mail errors, incidents critiques, backup absent.

### Alertes sécurité
Signatures webhook répétées invalides, cross-tenant, rate-limit massif, accès disabled/platform, hausse 401/403 — **sans payload sensible**.

### Rétention (aucune purge métier auto non approuvée)
Documents / extractions / analyses / écritures / deliveries / jobs / events / audits / logs / backups : **politique à valider juridiquement**.  
Cleanup V1 : dry-run par défaut.

### RGPD (non audit juridique)
Catégories : users, orgs, documents comptables, contacts, e-mails, logs, audits.  
Sous-traitants typiques : hébergeur PG, Stripe, OpenAI, Supabase, Brevo.  
Suppression org ≠ effacement RGPD — workflow futur documenté (pas construit).

---

## 25–26. Risques outbox / multi-instance

| Risque | Statut | Recommandation |
|--------|--------|----------------|
| Commit métier sans event (crash) | **connu** | Outbox transactionnelle V2 |
| Rate limiter mémoire V1 | **connu** | Redis ou gateway avant scale horizontal |
| Deux versions workers incompatibles | documenté | déploiement séquentiel |

Modules concernés outbox : Vault, Billing, Accounting, Delivery, Admin.

---

## 27–28. Anomalies / corrections Phase G

| ID | Sévérité | Correction |
|----|----------|------------|
| OpenAPI ouvert en prod | HIGH | `docs_url=None` si production |
| Workers in-process en prod | HIGH | désactivés hors non-prod |
| Dual gating env | MEDIUM | `elfis_environment \|\| app_env` |
| Stripe secrets soft en prod | HIGH | fatals startup |
| `PLATFORM_ADMIN` soft | HIGH | fatal |
| CORS `*` + credentials | HIGH | fatal prod |
| npm Windows CreateProcess | LOW | `npm.cmd` dans runner |

---

## 29–31. Fichiers

### Créés
- `backend/tests/production_readiness/*`
- `backend/scripts/production/*`
- `backend/docs/runbooks/*`, `backend/docs/deployment/*`
- `docs/runbooks/*`, `docs/deployment/*`
- `docs/functional-test-phase-g-report.md` (ce fichier)

### Modifiés
- `backend/app/security/security_startup.py`, `config.py`, `main.py` (session antérieure + consolidations)
- `backend/.env.example`, `.gitignore`
- `backend/scripts/run_functional_validation.py` (`--phase-g`, npm Windows)
- `docs/functional-testing-checklist.md` (PHASE G)

### Tests ajoutés
ENV-001…006, SECRET-*, ROUTE-*, AUTH-*, MIG-* (SQL), PROVIDER-*, WORKER-*, HEALTH-*, CORS, OpenAPI, backup docs, smoke guards.

---

## 32–36. Non-régression / FastAPI / frontend / réseau / limites

- Regression ciblée : 30 passed  
- FastAPI : OK  
- Frontend build : OK  
- Réseau réel : **0**  
- Limites : pas d’Alembic ; MIG Postgres live non exécuté ; TrustedHost = config proxy hébergeur ; RPO/RTO non décidés

---

## 37. Décisions bloquantes avant go-live

1. Exécuter **Phase F PostgreSQL réelle** (`ELFIS_PERFORMANCE_DATABASE_URL`)
2. Appliquer/valider migrations SQL + index sur **staging Postgres**
3. Fixer **RPO / RTO**
4. Activer flags enforcement billing/quotas selon produit
5. Plan **rate-limit multi-instance** (Redis/gateway)
6. Plan **outbox V2** ou acceptation risque écrite
7. Validation juridique rétention / sous-traitants
8. Checklist production signée (`backend/docs/deployment/production-checklist.md`)

---

## 38–39. Git

- **Aucun commit**
- **Aucun push**
