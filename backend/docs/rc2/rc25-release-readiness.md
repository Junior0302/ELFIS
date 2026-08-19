# RC2.5 Release Readiness

**Date :** 2026-07-23  
**Version cible :** RC2.5.1 → RC2.5.8  
**Décision :** **GO_DRY_RUN**

---

## Résumé

Le code RC2.5 est déployable avec **tous les flags off** (**GO_DISABLED** toujours valide).  
**GO_DRY_RUN** est maintenant autorisé : PostgreSQL staging + concurrence multi-workers certifiés (0 skip).  
**GO_PILOT / live : NON** (hors scope RC2.5.8 — bridge live non validé).

---

## Matrice audit (preuves)

| Domaine | Unit | Intégration | PostgreSQL réel | Frontend | Staging | Docs | Risque | Statut |
|---------|------|-------------|-----------------|----------|---------|------|--------|--------|
| Storage / Registry / versions / lifecycle | oui | oui | schema PASS | OK | stage1–4 | OK | faible | **PASS** |
| Processing Jobs | oui | oui | claim+lease+retry concurrent **PASS** | OK | stage1 | runbook | moyen | **PASS** |
| Classification / OCR / Extraction | oui | oui | schéma OK | OK | stage2–4 | OK | faible | **PASS** |
| Business Validation | oui | oui | schéma OK | revue processing | stage5 | OK | faible | **PASS** |
| Packages / Deliveries | oui | oui | claim+lease+idempotence+unknown **PASS** | `/elfadmin/integrations/documents` | stage5–6 | OK | moyen (unknown) | **PASS** |
| ComptaPilot Bridge | dry_run OK | mapper sans comptes | non-live | mode affiché | disabled | runbook | moyen | **PASS (disabled)** |
| IAM / Audit / Health | oui | oui | — | — | — | — | faible | **PASS** |
| Auth Phase A | **43 passed** | — | — | — | — | — | faible | **PASS** |
| Concurrence delivery/processing PG | 13 tests | — | **13 passed / 0 skipped** | — | workers manuels PASS | — | résiduel GO_PILOT | **PASS** |

---

## Environnement & SQL

- PostgreSQL **17.6** (Supabase pooler staging)
- 11 migrations RC2.5 appliquées + rejeu idempotent **PASS** (RC2.5.7)
- Checker : `python scripts/rc2/check_rc25_database_schema.py`
- Bridge : `COMPTAPILOT_DOCUMENT_BRIDGE_MODE=disabled` ; publish/auto-publish **false**

---

## RC2.5.8 — Concurrence (preuves)

| Commande / scénario | Résultat |
|---------------------|----------|
| `pytest tests/concurrency/test_postgres_*.py` (delivery + job) | **13 passed, 0 skipped** |
| 2 workers processing (`rc258-processing-a/b`) | **PASS** — un seul claim |
| 2 workers delivery noop (`rc258-delivery-a/b`) | **PASS** — 1 attempt, 1 `noop:` ref, b=0 |
| Lease recovery processing + delivery | **PASS** |
| Idempotence concurrente (`uq` + `duplicate_prevented`) | **PASS** |
| `unknown` + reconcile dry-run puis `--apply --confirm` | **PASS** → `manual_review`, 1 ext ref |
| Isolation tenant (list org + reconcile filter) | **PASS** |
| Nettoyage probes métier | **PASS** (audits/orgs probe conservés) |

### Cas A–J

| Cas | Statut |
|-----|--------|
| A Processing claim concurrent | PASS |
| B Processing lease recovery | PASS (`leases_recovered`) |
| C Processing retry concurrent | PASS |
| D Delivery claim concurrent | PASS |
| E Delivery lease recovery | PASS |
| F Delivery idempotency concurrent | PASS |
| G Un seul bridge call | PASS |
| H delivery_unknown sans retry aveugle | PASS |
| I reconciliation unknown | PASS |
| J isolation organisations | PASS (API/list/reconcile ; claim workers global by design) |

---

## Tests exécutés (RC2.5.8)

| Commande | Résultat |
|----------|----------|
| Concurrence PG (2 fichiers) | **13 passed, 0 skipped** |
| `tests/document_processing` | **18 passed** |
| `tests/product_integrations` | **15 passed** |
| `tests/document_business_validation` | **9 passed** |
| Auth Phase A (6 fichiers) | **43 passed** (réf.) |
| `npm run build` | **OK** |
| Routes FastAPI | **333** |

---

## Risques / limitations

1. Workers claim **cross-tenant** (pas de scope org au claim) — isolation via API/list/reconcile uniquement  
2. Bridge **live / GO_PILOT** non certifié  
3. Pooler Supabase : `prepare_threshold=None` requis pour tests PG  
4. Orgs/audits probe peuvent rester (politique conservation audit)

---

## Rollback

Voir `docs/runbooks/rc25-rollback.md`.

---

## Décision

| Option | Verdict |
|--------|---------|
| **GO_DISABLED** | **OUI** |
| **GO_DRY_RUN** | **OUI** — staging certifié, bridge non-live |
| GO_PILOT | **NON** — RC2.5.8 n’autorise pas GO_PILOT |
| NO_GO | Non |
