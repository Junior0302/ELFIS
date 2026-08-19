# ELFIS Core / ComptaPilot — Audit Global V1

| Champ | Valeur |
|-------|--------|
| Date | 2026-07-26 |
| Périmètre | ELFIS Core backend + frontend ComptaPilot |
| Nature | Lecture seule — **aucune correction métier appliquée** |
| Objectif | Analyser, mesurer, risques, doublons, dette, recommandations |

---

## 1. Résumé exécutif

ELFIS Core / ComptaPilot est une **plateforme SaaS comptable-IA riche**, déjà structurée en moteurs (Financial, Banking, Accounting V1/V2, AI Assistant, Jobs, Events, IAM, Observability). La documentation et les certifications de sprints sont **exceptionnellement denses** pour un produit à ce stade.

Le produit est **apte à un pilote / staging contrôlé**, mais **pas prêt pour un multi-tenant massif** sans travaux ciblés :

1. **Schéma & migrations** — pas d’Alembic ; dualité soft-SQLite / SQL PostgreSQL manuels.
2. **Scalabilité process-locale** — caches mémoire, rate-limit non partagé, Financial Engine en `.all()`.
3. **Empilements historiques** — triple stack IA, triple comptabilité, dual billing, dual dashboard, dual chat.
4. **Go-live commercial** — entitlements/quotas soft-off par défaut ; Dockerfile prod + SQLite incohérent ; **aucune CI `.github`**.

**Score global pondéré : 62 / 100**

Verdict : **pilote autorisé** · **production massive bloquée** tant que les risques critiques (DB, Docker, CI, Financial Engine, enforcement billing) ne sont pas traités.

---

## 2. Scores par domaine

| Domaine | Score | Commentaire court |
|---------|------:|-------------------|
| Architecture | **58 %** | Modules riches, empilements lourds |
| Sécurité | **72 %** | IAM/middleware solides, dette config/ops |
| Performance | **55 %** | Caches OK, N+1 / full-load critiques |
| Scalabilité | **38 %** | Process-local = plafond bas |
| Modules métier | **65 %** | Cœur mature, stubs & doublons |
| Frontend | **68 %** | Large couverture, parcours dupliqués |
| IA | **72 %** | Decision Engine fort, dual chat risqué |
| Base de données | **48 %** | SQL PG soigné, gouvernance migrations faible |
| Intégrations | **68 %** | Abstractions bonnes, OCR/LLM partiels |
| Observabilité | **78 %** | Point le plus abouti |
| Production | **55 %** | Docs excellents, packaging/CI faibles |
| Expérience produit | **64 %** | Docs +, onboarding léger |
| Commercialisation | **68 %** | Stripe/trial OK, enforcement soft-off |

**Moyenne simple : 62 %**

---

## 3. Architecture — 58 %

### Points forts

- Découpage en packages domaine (`financial`, `banking`, `billing`, `ai_assistant`, `jobs`, `events`, `iam`, `system_health`…).
- Façades de transition déjà amorcées (`finance_agent` → `DecisionEngine` / `FinancialEngine`).
- Event bus + jobs comme colonne vertébrale d’intégration.

### Points faibles / doublons

| Empilement | Preuve | Risque |
|------------|--------|--------|
| Triple IA | `ai/`, `ai_assistant/`, `elfis_ai/` + `routers/ai.py` + `routers/elfis_ai.py` | Critique (complexité) |
| Triple comptabilité | `accounting/`, `accounting_engine/`, `accounting_intelligence/` | Important |
| Dual dashboard | `/api/dashboard/*` vs `/api/financial/*` | Important |
| Dual billing | `subscriptions` + `billing` + `saas_billing` + sales `/billing` | Important |
| Documents fragmentés | `document_intake`, `document_analysis`, `document_extraction`, `document_processing` | Important |
| `services/` + `routers/` fourre-tout | legacy côte à côte des packages | Important |

### Recommandations

1. Cartographier une **architecture cible** (un moteur = une vérité) et un plan de dépréciation.
2. Unifier les surfaces chat IA et dashboard financier.
3. Extraire Vault en package top-level (aujourd’hui `services/vault/`).

---

## 4. Sécurité — 72 %

### Points forts

- IAM Permission Engine (`app/iam/`), RBAC, rôles plateforme.
- `SecurityMiddleware` : headers, payload limits, rate categories, redaction.
- Startup asserts prod (JWT faible / CORS `*` refusés) dans `config.py` / `security_startup.py`.
- Audit trail dédié (`app/audit/`).

### Risques

| Risque | Preuve | Niveau |
|--------|--------|--------|
| `AUTH_REQUIRED=false` → `permissions=["*"]` | `deps.py` | Critique (ops) |
| JWT / CORS défauts dangereux hors prod | `config.py` | Critique si mauvaise config |
| Rate-limit in-memory + `X-Forwarded-For` | `security_rate_limit.py` | Important |
| CSP report-only / HSTS off par défaut | `config.py`, `security_headers.py` | Important |
| Routes `/financial/*` sans permission fine (subscription seule) | `financial/api/routes.py` | Important |
| FK `organization_id` manquantes sur modèles legacy / banking / assistant | `models.py`, `banking_models.py`, `ai_assistant/models.py` | Important |

### Recommandations

1. Interdire explicitement `auth_required=False` hors tests.
2. Rate-limit Redis (ou équivalent) multi-instance.
3. Durcir CSP / HSTS en staging puis prod.
4. Ajouter `auth.require(...)` sur les endpoints financiers sensibles.
5. FK tenant sur tout le cœur métier.

---

## 5. Performance — 55 %

### Points forts

- Caches TTL : financial (60 s), health (~15 s), assistant (45 s), permissions (30 s).
- Pagination bornée Search / platform admin / listes accounting.
- Streaming assistant (SSE) et workers jobs avec retry.

### Points faibles

- **Financial Engine** charge en mémoire `SalesDocument`, `Invoice`, `BankTransaction` via `.all()` (`financial/engine.py`) — N×M en RAM.
- Vue plateforme finance : jusqu’à **500 orgs** × snapshot complet (`platform_service.py`).
- `elfis_ai/chat.py` charge jusqu’à 100 invoices sans Decision Engine.
- Métriques / caches process-local (pas de partage horizontal).

### Optimisations prioritaires

1. Remplacer les `.all()` du Financial Engine par agrégats SQL / fenêtres temporelles.
2. Matérialiser (ou cacher Redis) les snapshots org.
3. Paginer / limiter strictement les vues plateforme.
4. Exporter metrics Prometheus / OTel.

---

## 6. Scalabilité — 38 %

### Projection

| Organisations | Évaluation | Points de blocage |
|--------------:|------------|-------------------|
| **100** | Acceptable (Postgres + workers) | Snapshot financier lourd sur grosses orgs |
| **1 000** | Fragile | Caches/rate-limit non partagés ; overview plateforme O(n) |
| **10 000** | Bloqué | Full-table loads ; jobs claim sans coordination partagée documentée ; outbox non transactionnelle |
| **100 000** | Impossible sans refonte | Architecture process-local + absence sharding / queues distribuées |

### Recommandations

1. Outbox transactionnelle (documentée Phase G comme V2 non livrée).
2. Redis (cache, rate-limit, locks jobs).
3. Workers horizontaux + claim atomique.
4. Agrégats pré-calculés (Financial Health / KPIs) asynchrones.

---

## 7. Modules métier — 65 %

| Module | Maturité | Doublons / écarts |
|--------|----------|-------------------|
| Vault / Documents | Complet | — |
| Accounting V1 | Partiel | Export FEC stub |
| Accounting Engine V2 | Partiel→Complet | Peu de tests |
| Accounting Intelligence | Partiel | Chevauche `/intelligence` |
| Banking | Partiel | Demo mature ; Bridge/Powens config-dépendants |
| Billing commercial (sales) | Complet | Préfixe `/billing` ambigu avec SaaS |
| Billing SaaS / Stripe | Partiel (dual) | `subscriptions` + Billing V2 |
| Financial | Complet V1 | Perf `.all()` |
| AI Assistant | Complet V1 | — |
| ELFIS AI | Partiel | Chat heuristique |
| Search | Complet | `bank_transaction` non indexé |
| Notifications | Complet | Polling FE (pas SSE) |
| Jobs | Complet | Scale multi-instance fragile |
| Delivery / email | Partiel→Complet | Config multi-transport complexe |

### Fonctionnalités incomplètes notables

- Export FEC / écritures définitives limitées.
- OCR réel (défaut `noop`).
- Outbox events.
- RGPD workflow (Phase G : non construit).
- Enforcement quotas/entitlements désactivé par défaut.

---

## 8. Frontend — 68 %

### Points forts

- Lazy routes, nav par permissions, guides vocaux, cockpit plateforme séparé.
- Signaux a11y (`sr-only`, `focus-visible`, `prefers-reduced-motion`, roles).
- Pages Financial Dashboard + AI Assistant modernes.

### Doublons / parcours complexes

| Paire | Impact |
|-------|--------|
| `/dashboard` vs `/finance` | Deux « tableaux de bord » |
| `/copilote` vs `/intelligence` | Deux chats / signaux IA |
| Accounting hub / engine / intelligence | Trois portes d’entrée |
| `/elfadmin/*` très dense | Charge cognitive admin |

### Recommandations

1. Fusionner Accueil → Financial Dashboard (ou clairement hiérarchiser).
2. Un seul chat produit (Decision Engine) ; `/intelligence` = signaux uniquement.
3. Audit a11y systématique (axe) sur pages legacy.

---

## 9. IA — 72 %

### Points forts

- Decision Engine : outils → faits déterministes → LLM optionnel → anti-hallucination (`merge_llm_enrichment`).
- Réponses 4 sections + explainability + feedback + observabilité runs.
- Pricing registry (`ai_usage.py`) pour `gpt-4o-mini`.

### Points faibles

- Dual chat `/ai/chat` (Decision Engine) vs `/elfis-ai/chat` (heuristiques, sans mêmes garde-fous).
- Triple package `ai` / `ai_assistant` / `elfis_ai`.
- Coût estimé null pour modèles hors registry.
- Garde anti-hallucination heuristique (tokens `€`) — perfectible.

### Recommandations

1. Déprécier le chat heuristique ou le brancher sur le Decision Engine.
2. Étendre le pricing registry.
3. Tests d’hallucination adversariaux en CI.

---

## 10. Base de données — 48 %

### Points forts

- Nombreux scripts SQL PostgreSQL versionnés (`backend/sql/*.sql`).
- Indexes Phase F documentés.
- Nouveaux modules RC2 avec FK + Index composés.

### Points faibles

- **Pas d’Alembic** — migrations manuelles + `create_all`.
- Soft ALTER SQLite (`_sqlite_add_column_if_missing`) **non appliqué sur PG** → drift.
- FK absentes sur cœur legacy (`Invoice.organization_id`, banking, assistant).
- Ordre d’import FK `document_intake` ↔ `migration_center` historiquement fragile.

### Recommandations

1. Introduire Alembic (ou outil équivalent) comme source unique.
2. Aligner soft migrations et SQL PG.
3. FK tenant + contraintes d’intégrité sur legacy.

---

## 11. Intégrations — 68 %

| Intégration | Robustesse | Interchangeabilité | Retries / erreurs |
|-------------|------------|--------------------|-------------------|
| Stripe | Bonne (signature, idempotence) | Provider string | Dual stack legacy/V2 |
| Banking Bridge/Powens | Bonne (registry, retryable) | Connecteurs interchangeables | `banking_sync_max_attempts` |
| Email (Brevo/SMTP/OAuth) | Bonne | Multi-transport | Crypto Fernet sensible |
| OCR | Faible (noop défaut) | Registry providers | Non prod-ready image |
| LLM OpenAI | Moyenne | Quasi mono-provider | Timeout config |
| Storage Supabase/local | Bonne | Registry | `supabase_storage_max_retries` |

---

## 12. Observabilité — 78 %

### Points forts

- `/api/health/live|ready|details`, `/api/metrics`, System Health Center admin.
- Audit engine, correlation IDs, structured logging.
- Runs assistant (latence, tokens, coût, outils, cache).
- Docs `docs/observability.md` + validations RC2.

### Points faibles

- Métriques in-memory (pas d’export Prometheus/OTel standard).
- Health public legacy un peu verbeux.
- Fragmentation obs assistant vs plateforme.

---

## 13. Production — 55 %

### Points forts

- Runbooks riches : backup, rollback, secret-rotation, Stripe incident.
- Checklists `production-readiness`, RC1/RC2.
- `.env.example` propres ; `.env` gitignoré.
- Asserts startup en production.

### Points faibles

| Finding | Preuve | Niveau |
|---------|--------|--------|
| Dockerfile force `DATABASE_URL=sqlite` + `APP_ENV=production` | `backend/Dockerfile` | Critique |
| Aucun pipeline CI/CD `.github/` | dépôt | Critique |
| Pas de docker-compose multi-services | — | Important |

---

## 14. Expérience produit — 64 %

| Axe | État |
|-----|------|
| Onboarding | Checklist dashboard si empty ; pas de product tour |
| Emails | Templates billing/system/sales clairs |
| Erreurs | `UiStates` + messages FR billing ; parfois HTTP brut |
| Documentation | ~139 MD — atout majeur |
| Prise en main | Dense (trop d’entrées menu) |

---

## 15. Commercialisation — 68 %

| Capacité | État | Risque |
|----------|------|--------|
| Essai 14 j | Complet | Faible |
| Plans / FeatureCodes | Complet | Faible |
| Quotas / entitlements | Code prêt, **enforce = False** | Critique go-live |
| Stripe checkout / portal / cancel | Complet | Moyen (dual stack) |
| Support | Partial (cockpit support) | Moyen |
| Conformité RGPD | Hints / Phase G non construit | Critique juridique |

---

## 16. Dette technique priorisée

### Critique

1. Absence d’Alembic / drift schéma SQLite↔PG.
2. Dockerfile production + SQLite.
3. Absence de CI/CD.
4. Financial Engine `.all()` (scalabilité).
5. `AUTH_REQUIRED=false` → permissions `*`.
6. Entitlements/quotas soft-off par défaut.
7. Triple stack IA + dual chat produit.

### Importante

1. Dual billing (subscriptions vs Billing V2) + préfixe `/billing` ambigu.
2. Dual dashboard `/dashboard` vs `/finance`.
3. Rate-limit / caches process-local.
4. Outbox events non transactionnelle.
5. FK tenant manquantes (legacy, banking, assistant).
6. CSP report-only / HSTS off.
7. OCR noop ; export FEC stub.
8. Documents pipeline fragmenté (sprint vs RC2).
9. Vue plateforme finance O(n) snapshots.
10. RGPD / rétention non industrialisés.

### Faible

1. Vault hors package top-level.
2. Health public legacy verbeux.
3. Notifications en polling (pas SSE).
4. Pricing LLM registry étroit.
5. Façades legacy (`finance_agent`) — dette maîtrisée, à supprimer après bascule totale.

---

## 17. Recommandations stratégiques (ordre suggéré)

| Priorité | Action | Domaines impactés |
|----------|--------|-------------------|
| P0 | CI (lint, tests, typecheck) + corriger Dockerfile (PG obligatoire) | Production, Qualité |
| P0 | Activer enforcement entitlements/quotas en staging | Commercialisation |
| P0 | Agrégats SQL Financial Engine | Perf, Scalabilité |
| P1 | Alembic + unifier migrations | Base de données |
| P1 | Unifier chat IA (déprécier heuristique) | IA, Frontend, Architecture |
| P1 | Redis cache + rate-limit | Sécurité, Scalabilité |
| P2 | Fusionner dashboards FE | Frontend, Produit |
| P2 | Unifier billing SaaS | Modules, Commercialisation |
| P2 | Outbox + workers horizontaux | Scalabilité, Jobs |
| P3 | OCR réel, FEC, RGPD workflows | Modules, Conformité |

---

## 18. Tableau de certification

| Domaine | Score |
|---------|------:|
| Architecture | **58 %** |
| Sécurité | **72 %** |
| Performance | **55 %** |
| Scalabilité | **38 %** |
| Modules métier | **65 %** |
| Frontend | **68 %** |
| IA | **72 %** |
| Base de données | **48 %** |
| Intégrations | **68 %** |
| Observabilité | **78 %** |
| Production | **55 %** |
| Expérience produit | **64 %** |
| Commercialisation | **68 %** |
| **GLOBAL** | **62 %** |

---

## 19. Conclusion

L’audit n’a **modifié aucun comportement métier**. Les constats s’appuient sur le code, la configuration, les docs et les structures de tests existants.

**Forces** : moteurs métier récents (Financial, Banking, AI Assistant), IAM, observability, documentation, abstractions d’intégration.

**Faiblesses** : dette d’empilement, gouvernance DB, packaging/CI, scalabilité process-locale, go-live commercial soft-gated.

**GLOBAL AUDIT COMPLETED**
