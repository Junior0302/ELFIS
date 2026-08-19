# Accounting Intelligence V2 — Rapport de certification

**Date :** 2026-07-24  
**Verdict :** **ACCOUNTING INTELLIGENCE V2 CERTIFIED**

Migration Center inchangé. Aucune écriture comptable automatique.

---

## 1. Architecture

Package `backend/app/accounting_intelligence/` :

| Composant | Rôle |
|-----------|------|
| `recommendation_engine.py` | Priorité règles → prefs → historique → similarité → IA |
| `learning_engine.py` | Apprentissage gated (accept/modify complets uniquement) |
| `memory.py` | Historique versionné `LearningMemory` |
| `explanation_engine.py` | Explications humaines (compte, TVA, journal, score, confiance) |
| `rule_optimizer.py` | Propositions d’optimisation — jamais d’auto-modif |
| `context_engine.py` | Profil tenant (comptes, journaux, TVA, exceptions) |
| `similarity_engine.py` | Score similarité + cache |
| `feedback.py` | Accept / modify / reject + durée + commentaire |
| `events.py` / `audit.py` | Traçabilité complète |
| `service.py` | Orchestration API |

Réutilise : Accounting Engine (RuleEngine, VATEngine, JournalResolver, ConfidenceEngine, Learning foundation, ProposalService), event bus, IAM.

---

## 2. Confiance enrichie

`ConfidenceEngine` intègre désormais : extraction, validation, cohérence, historique/apprentissage, similarité, score IA — détail exposé dans chaque recommandation.

---

## 3. API `/api/accounting/intelligence`

| Endpoint | Permission |
|----------|------------|
| GET/POST `/recommendations` | `accounting_intelligence.read` |
| GET `/explanations` | `accounting_intelligence.read` |
| GET `/learning` | `accounting_intelligence.read` |
| POST `/feedback` | `accounting_intelligence.feedback` |
| POST `/retrain` | `accounting_intelligence.retrain` |
| GET/POST `/similarity` | `accounting_intelligence.read` |

Events : `learning.created`, `feedback.received`, `recommendation.generated|accepted|modified|rejected` (suffixe `.v1`).

---

## 4. Frontend

- `AccountingIntelligencePanel` — propositions, explications, confiance, historique, appris, avant/après, feedback
- Page `/accounting/intelligence` + nav « Intelligence V2 »

---

## 5. PostgreSQL (additif)

SQL : `elfis_accounting_intelligence_v2_postgres.sql`

Tables : `elfis_ai_context_profiles`, `elfis_ai_learning_memory`, `elfis_ai_recommendation_history`, `elfis_ai_feedback`, `elfis_ai_similarity_cache`, `elfis_ai_audit`

Certif : `accounting-intelligence-v2-postgres-certification.json` → `certified: true`

---

## 6. Tests

| Suite | Résultat |
|-------|----------|
| Intelligence V2 pytest | **7 PASS** |
| Engine V2 régression | **7 PASS** |
| FE intelligence API | **1 PASS** |
| FE build | **OK** |
| PG staging | **certified: true** |
| Routes | **418** |

---

## 7. Limites

- IA = heuristique profil local (pas de LLM externe dans cette phase)
- Apprentissage uniquement après feedback accept/modify complet
- RuleOptimizer propose, ne mute jamais les règles

---

# ACCOUNTING INTELLIGENCE V2 CERTIFIED
