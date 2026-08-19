# Migration Center — Rapport technique Stage 2 (certification)

Date certification : **2026-07-23**  
Environnement PostgreSQL : **staging Supabase PG 17.6** (`ELFIS_RC1_DATABASE_URL`, host redacté)  
Verdict : **STAGE 2 CERTIFIED**

---

## 1. Certification PostgreSQL (réelle)

Script : `backend/scripts/migration/certify_stage2_postgres.py`  
Preuve JSON : `backend/docs/migration/stage2-postgres-certification.json`

| Scénario | Description | Résultat |
|----------|-------------|----------|
| **A** | Base sans tables migration → Sprint1 + Stage2 | **PASS** |
| **B** | Base Sprint1 seule → Stage2 | **PASS** |
| **C** | Rejeu Stage2 (idempotence) | **PASS** |
| API boot | Import `app.main` après migration | **PASS** (345 routes) |

### Correctif SQL critique (certification)

Les défauts JSONB `'{"schema_version":1,...}'` étaient interprétés par SQLAlchemy `text()` comme bind `:1`.  
Remplacés par `jsonb_build_object('schema_version', 1, 'data', jsonb_build_object())`.

### Tables vérifiées

- `elfis_migration_sessions`
- `elfis_migration_timeline_entries`
- `elfis_migration_activities`
- `elfis_migration_memory_entries`

### Colonnes Stage 2 vérifiées

- `migration_session_token` (UNIQUE + index)
- `migration_profile` / `ai_profile` (JSONB défauts `schema_version=1`)

### Contraintes / index / FK / unicité token

Vérifiés via `pg_constraint` / `pg_indexes` / probe INSERT doublon token → **rejeté**.  
Probe JSONB defaults → `schema_version == 1`.  
FK vers `organizations` / `elfis_migration_sessions` / `users` présentes.

---

## 2. Matrice exigences / tests

| # | Exigence | Fichier de test | Nom du test | Résultat | Couverture |
|---|----------|-----------------|-------------|----------|------------|
| 1 | Token généré backend | `test_stage2_architecture.py` | `test_token_auto_generated_unique_immutable` | PASS | couvert |
| 2 | Token unique | idem | idem | PASS | couvert |
| 3 | Token immuable | idem | idem | PASS | couvert |
| 4 | Token refusé payloads | `test_stage2_certification_matrix.py` | `test_token_rejected_in_create_payload` | PASS | couvert |
| 5 | `get_by_session_token` isolé | `test_stage2_architecture.py` | `test_get_by_token_tenant_isolation` | PASS | couvert |
| 6 | `migration_profile` init | `test_stage2_architecture.py` | `test_profiles_initialized_and_separated` | PASS | couvert |
| 7 | `ai_profile` init | idem | idem | PASS | couvert |
| 8 | Séparation profils | idem | idem | PASS | couvert |
| 9 | Timeline à la création | `test_stage2_architecture.py` | `test_timeline_create_complete_duration_no_dup` | PASS | couvert |
| 10 | Start étape idempotent | `test_stage2_certification_matrix.py` | `test_start_and_complete_step_idempotent` | PASS | couvert |
| 11 | Complete étape idempotente | idem | idem | PASS | couvert |
| 12 | `duration_ms` backend | `test_stage2_architecture.py` | `test_timeline_create_complete_duration_no_dup` | PASS | couvert |
| 13 | Pas de doublon retry | `test_stage2_certification_matrix.py` + API | start/complete + timeline count | PASS | couvert |
| 14 | Activité à la création | `test_stage2_architecture.py` | `test_activity_feed_on_create_profile_sources` | PASS | couvert |
| 15 | Activité profil | idem | idem | PASS | couvert |
| 16 | Activité sources | idem | idem | PASS | couvert |
| 17 | Reprise session active | `test_stage2_architecture.py` | `test_resume_active_refuse_cancelled_completed` | PASS | couvert |
| 18 | Reprise double-clic | `test_stage2_certification_matrix.py` | `test_resume_double_click_idempotent_activity` | PASS | couvert |
| 19 | Refus resume cancelled | `test_stage2_architecture.py` | `test_resume_active_refuse_cancelled_completed` | PASS | couvert |
| 20 | Refus resume completed | idem | idem | PASS | couvert |
| 21 | Isolation timeline | `test_stage2_architecture.py` | `test_timeline_activity_tenant_isolation` | PASS | couvert |
| 22 | Isolation activités | idem | idem | PASS | couvert |
| 23 | Progression initiale | `test_stage2_architecture.py` | `test_progress_initial_and_after_steps` | PASS | couvert |
| 24 | Progression après profil | idem | idem | PASS | couvert |
| 25 | Progression après sources | idem | idem | PASS | couvert |
| 26 | `overall_percent` non FE | idem | idem | PASS | couvert |
| 27 | Source beta OK | `test_stage2_architecture.py` | `test_source_beta_maintenance_deprecated` | PASS | couvert |
| 28 | Source maintenance refusée | idem | idem | PASS | couvert |
| 29 | Deprecated refusée nouvelle | idem | idem | PASS | couvert |
| 30 | Deprecated lisible existante | idem | idem | PASS | couvert |
| 31 | Événements publiés | `test_stage2_certification_matrix.py` | `test_event_payload_required_fields_and_no_sensitive` | PASS | couvert |
| 32 | Payload sans sensible | idem | idem | PASS | couvert |
| 33 | Memory scope=session | `test_stage2_architecture.py` | `test_memory_session_scope_only_and_tenant` | PASS | couvert |
| 34 | Refus scope=organization | `test_stage2_certification_matrix.py` | `test_memory_refuse_organization_and_product_scopes` | PASS | couvert |
| 35 | Refus scope=product | idem | idem | PASS | couvert |
| 36 | Isolation Memory | `test_stage2_architecture.py` | `test_memory_session_scope_only_and_tenant` | PASS | couvert |
| 37 | Optimiste nouveaux flux | `test_stage2_certification_matrix.py` + API | continue/cancel/version | PASS | couvert |
| 38 | Activité ≠ audit | `test_stage2_certification_matrix.py` | `test_activity_and_timeline_distinct_from_audit` | PASS | couvert |
| 39 | Timeline ≠ audit | idem | idem | PASS | couvert |
| 40 | Non-régression Sprint 1 | `test_sprint1_service.py` | suite Sprint 1 | PASS | couvert |

**Événements `.v1`** : `test_event_names_use_v1_suffix` — PASS.

**Cohérence moteurs** : `test_stage2_coherence.py::test_coherence_draft_to_awaiting_upload_cancel_resume_paths` — PASS  
(transitions draft→profile_completed→sources_selected→awaiting_upload + resume + cancel).

---

## 3. Scénario API complet

### SQLite / TestClient

`test_stage2_api_routes.py::test_api_full_scenario_and_cross_tenant_404` — **PASS**

### PostgreSQL staging

`test_stage2_postgres_integration.py::test_postgres_full_api_scenario_isolation_events` — **PASS**  
(`ELFIS_POSTGRES_TESTS_ENABLED=true`)

Couvre : create → read → token → timeline → activities → progress → profile → continue → sources → continue → resume×2 (1 activité) → events → 404 cross-org → cleanup.

### Correctif API (certification)

`AuthContext.user_id` manquait → `AttributeError` masqué en 400.  
Ajout propriété `user_id` dans `app/deps.py` (alignement usage API migration).

---

## 4. Preuves transverses

| Preuve | Statut |
|--------|--------|
| Isolation organisation (timeline/activités/progress/memory/API) | **démontrée** |
| Idempotence SQL Stage2 | **démontrée** (scénario C) |
| Absence doublons timeline / resume | **démontrée** |
| Progression backend-only | **démontrée** |
| Events `.v1` + payload minimal | **démontrée** |
| Activité / timeline distincts de l’audit | **démontrée** |

---

## 5. Résultats tests & build

| Suite | Résultat |
|-------|----------|
| Backend `tests/migration_center` | **36 passed** (dont 1 PG si enabled) |
| Frontend vitest migration | **11 passed** |
| `npm run build` | **OK** |
| Routes FastAPI | **345** |

Frontend : Vitest (stack existante) — pas d’ajout RTL ; helpers couvrent progression API, badges, resume, absence d’estimation, non-recalcul local.

---

## 6. Fichiers certification ajoutés / touchés

- `scripts/migration/certify_stage2_postgres.py`
- `scripts/migration/inspect_mig_pg.py`
- `sql/elfis_migration_center_stage2_postgres.sql` (fix bind JSONB)
- `tests/migration_center/test_stage2_certification_matrix.py`
- `tests/migration_center/test_stage2_coherence.py`
- `tests/migration_center/test_stage2_api_routes.py`
- `tests/migration_center/test_stage2_postgres_integration.py`
- `app/deps.py` (`user_id`)
- `app/migration_center/service.py` (resume idempotent + event `step.started`)
- Rapport + `stage2-postgres-certification.json`

---

## 7. Limites restantes

- Pas de statut `paused` (volontaire).
- Memory sans endpoint public.
- Estimation temps toujours `null`.
- FE tests = Vitest helpers (pas RTL e2e navigateur).
- Staging `public.users` vide hors user éphémère de certif.
- Aucun upload / OCR / IA / import (hors périmètre).

---

## 8. Verdict

# STAGE 2 CERTIFIED

Conditions remplies :

- SQL Stage2 **réellement appliqué** sur PostgreSQL (A/B/C)
- Tests critiques présents et verts
- Isolation tenant démontrée
- Actions répétées sans doublons incohérents
- Progression non contrôlée par le frontend

**Recommandation** : ouvrir le Sprint 2 (upload + jobs) sur cette base certifiée.
