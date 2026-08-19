# Accounting Engine V2 — Rapport de fondation

**Date :** 2026-07-24  
**Verdict :** **ACCOUNTING ENGINE FOUNDATION CERTIFIED**

Le Migration Center V1 n’a pas été modifié. Aucune écriture comptable définitive n’est produite.

---

## 1. Architecture

Package `backend/app/accounting_engine/` :

| Composant | Rôle |
|-----------|------|
| `engine.py` | Orchestration pipeline V2 |
| `proposal_service.py` | Persistance, generate/regenerate, lecture |
| `rule_engine.py` | Analyse direction / type / hints comptes |
| `account_resolver.py` | Résolution comptes (règles → settings → learning → défauts PCG) |
| `journal_resolver.py` | ACH / VTE / BQ / CAISSE / OD |
| `vat_engine.py` | HT / TVA / TTC, incohérences, exonération |
| `consistency_engine.py` | Débit=crédit, TVA, montants, dates, devise, comptes |
| `confidence_engine.py` | Score global (extraction, validation, historique, règles, cohérence) |
| `learning.py` | Mémoire validations utilisateur (sans rules globales) |
| `events.py` / `audit.py` | Events + audit trail |
| `api/routes.py` | Endpoints `/api/accounting/*` |

Réutilise : `map_accounting`, `CompanySettings`, `balance_tolerance`, event bus, IAM catalog.

---

## 2. Pipeline

```
Document validé / payload métier
  → RuleEngine
  → AccountResolver (+ LearningEngine lookup)
  → VATEngine
  → JournalResolver
  → Lignes (map_accounting achats / construction ventes)
  → ConsistencyEngine
  → ConfidenceEngine
  → Proposition V2 (statut generated | requires_review)
```

Disclaimer explicite : proposition uniquement.

---

## 3. API

Préfixe `/api/accounting` (router V2) :

| Méthode | Endpoint | Permission |
|---------|----------|------------|
| GET | `/proposal` | `accounting_engine.read` |
| POST | `/generate` | `accounting_engine.generate` |
| POST | `/regenerate` | `accounting_engine.regenerate` |
| GET | `/confidence` | `accounting_engine.read` |
| GET | `/explanation` | `accounting_engine.read` |

---

## 4. Frontend

- `AccountingProposalPanel` — journal, comptes, TVA, score, explications, warnings, historique, comparaison avant/après
- Page `/accounting/engine` + nav « Moteur V2 »
- Client `accountingEngineApi.ts`

---

## 5. PostgreSQL (migration additive)

SQL : `backend/sql/elfis_accounting_engine_v2_postgres.sql`

Tables :

- `elfis_chart_of_accounts`
- `elfis_accounting_engine_proposals`
- `elfis_accounting_learning_memory`
- `elfis_accounting_engine_audit`

Certif staging : `accounting-engine-v2-postgres-certification.json` → `certified: true` (apply + idempotent + contraintes).

---

## 6. Tests

| Suite | Résultat |
|-------|----------|
| `tests/accounting_engine/test_accounting_engine_v2.py` | **7 PASS** |
| FE `accountingEngineApi.test.ts` | **1 PASS** |
| FE build | **OK** |
| PG certify | **certified: true** |
| Routes app | **410** |

Couverture : facture achat, vente, avoir, sans TVA, multi-lignes/cohérence, regenerate, confidence, explanation, learning, cross-tenant, invoice model, permissions catalog.

---

## 7. Matrice exigences

Voir `backend/docs/migration/accounting-engine-v2-requirements-matrix.md`.

---

## 8. Limites (volontaires)

- Pas de validation automatique / posting.
- Pas de Modification du Migration Center.
- Apprentissage local org uniquement (pas de règles globales auto).
- IA account resolution : priorité bas niveau (defaults), pas de provider LLM dédié dans cette fondation.

---

# ACCOUNTING ENGINE FOUNDATION CERTIFIED
