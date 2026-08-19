# Rapport Phase F — Performance, concurrence, workers, montée en charge

Date : 2026-07-21  
Environnement : `ELFIS_ENVIRONMENT=test` · SQLite recette · mocks · **0 appel réseau réel**  
Commandes : `python scripts/run_functional_validation.py --phase-f` · `python scripts/performance/run_phase_f.py --quick`  
Commit / push : **aucun**

---

## 1. Environnement

- Base : SQLite (mode local rapide)
- Postgres concurrence : **non exécuté** dans cette session (pas d’URL dédiée) — procédure documentée
- Workers : claim simulé 2 sessions StaticPool
- Dataset lourd 5k : non généré en mode rapide (configurable via env futures)

---

## 2–4. Dataset / routes / baselines

Voir `docs/performance-baseline.md`.

Routes mesurées : health, vault list, search, platform dashboard, jobs list (taille bornée).

---

## 5–11. Concurrence / workers / quotas / isolation

| Test | Résultat SQLite | Postgres |
|------|-----------------|----------|
| Job claiming unique | PASS (optimiste) | À valider SKIP LOCKED |
| Event claiming unique | PASS | À valider |
| Quota limit=1 | PASS (UPDATE conditionnel) | À valider sous charge |
| Validation comptable unique | PASS (UPDATE status) | À valider |
| Delivery même clé | PASS (1 mail mock) | Threads TestClient = limité SQLite |
| Webhook event_id | PASS (1 ligne) | À valider |
| Vault doublon | PASS (409/reuse) | Unique partiel SQL |
| Isolation Search | PASS | — |
| Stale job dédupliqué | PASS | — |

---

## 12. Résultats PostgreSQL

**Restant à exécuter** :

```bash
$env:ELFIS_PERFORMANCE_DATABASE_URL='postgresql://…recette…'
python scripts/performance/run_phase_f.py --postgres
```

Sans cette URL, Phase F locale est **validée avec réserves** documentées (pas de faux positifs SKIP LOCKED).

---

## 13. Index

- Existants : jobs claim, events claim, vault checksum, search GIN (sql/*.sql)
- Ajouté : index unique `uq_document_email_org_idempotency` (init_db SQLite + `docs/performance/postgres_indexes_phase_f.sql`)
- Pool DB : `pool_pre_ping`, `pool_size`, `max_overflow`, `pool_recycle`, `pool_timeout` (Postgres)

---

## 14–16. Anomalies / corrections / avant-après

### PHF-F-001 — Quota over-consume sous concurrence

| | |
|--|--|
| **Sévérité** | CRITICAL |
| **Cause** | `check()` puis `UPDATE used+amount` sans borne |
| **Correction** | `UPDATE … WHERE used+reserved+amount <= limit` + `rowcount` |
| **Test** | `test_conc_003_quota_atomicity` |

### PHF-F-002 — Double validation comptable

| | |
|--|--|
| **Sévérité** | HIGH |
| **Cause** | Transition status non atomique |
| **Correction** | `UPDATE … WHERE status IN (ready, requires_review)` |
| **Test** | `test_conc_004_accounting_validation_unique` |

### PHF-F-003 — Delivery : quota avant idempotence + race insert

| | |
|--|--|
| **Sévérité** | CRITICAL |
| **Cause** | Consommation quota avant contrôle clé ; insert log non unique |
| **Correction** | Ordre idempotence → quota ; index unique org+clé ; catch `IntegrityError` |
| **Test** | `test_conc_005_delivery_idempotency_concurrency` |

### PHF-F-004 — Webhook Stripe double apply

| | |
|--|--|
| **Sévérité** | HIGH |
| **Cause** | Après `IntegrityError`, ré-application si status `received` |
| **Correction** | Retour `idempotent/in_progress` sans ré-apply |
| **Test** | `test_conc_006_webhook_event_id_concurrent` |

---

## 17–18. Multi-instance / outbox

**Multi-instance** : rate limiter mémoire, caches locaux — **non adaptés** au scale horizontal sans Redis/équivalent.

**Outbox** : pas d’outbox transactionnelle généralisée. Risque résiduel : commit métier puis crash avant publish event (Vault, accounting, delivery). Réconciliation via jobs/retry/admin. Recommandation V2 : outbox par module critique.

---

## 19–21. Fichiers / tests

**Créés** : `tests/performance/*`, `tests/concurrency/*`, `scripts/performance/run_phase_f.py`, `docs/performance/*`, ce rapport, `docs/performance-baseline.md`.

**Modifiés** : `quota_service.py`, `accounting_service.py`, `document_delivery.py`, `sales_email.py`, `stripe_webhook_handler.py`, `database.py`, `config.py`, `run_functional_validation.py`, checklist.

**Tests** : 20 Phase F (perf + conc).

---

## 22–25. Résultats

```
API latency.................... PASS
Pagination..................... PASS
Search performance............. PASS
Platform dashboard............. PASS
Job concurrency................ PASS
Event concurrency.............. PASS
Quota atomicity................ PASS
Accounting concurrency......... PASS
Delivery concurrency........... PASS
Webhook concurrency............ PASS
Vault concurrency.............. PASS
Tenant isolation under load.... PASS
Worker recovery................ PASS
Database connections........... PASS
Rate limiting.................. PASS (smoke ; mémoire V1 documentée)
Controlled degradation......... PASS (documenté / best-effort)

Phase F tests................... 20 passed
Regression tests............... 71 passed (billing+jobs+events+accounting)
FastAPI import................. OK (250 routes)
Frontend build................. OK
Real network calls............. 0
Known critical concurrency bugs 0
```

---

## 26–28. Risques / git

- Postgres SKIP LOCKED / soak / dataset 5k non exécutés ici
- Exactly-once provider e-mail externe non garanti
- Rate limit non distribué
- Outbox V2

Aucun commit. Aucun push.
