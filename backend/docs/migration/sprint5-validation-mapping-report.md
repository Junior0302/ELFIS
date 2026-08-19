# Sprint 5 — Validation & Mapping Center V1 — Rapport

**Date :** 2026-07-23  
**Verdict :** **SPRINT 5 CERTIFIED**

---

## 1. Architecture

Module `validation_mapping` : sessions de validation humaine sur extractions Sprint 4, édition contrôlée, historique append-only, détection de doublons documentaires, matching contacts (propositions). **Aucun import**, **aucune création automatique** de fiche métier.

Lifecycle document :
`awaiting_validation` → `human_validating` → `validated_by_user` → `ready_for_import`  
(+ `rejected`)

## 2–3. Fichiers

**Créés :** module complet `app/validation_mapping/*`, SQL `elfis_validation_mapping_sprint5_postgres.sql`, tests, FE `MigrationValidationPanel` + `validationApi`, scripts cert PG, matrice, ce rapport.

**Modifiés :** `document_intake/enums.py`, `lifecycle_service.py`, `main.py`, IAM, `event_types.py`, `migrate_sql.py`, `MigrationWizardPage.tsx` (étape 6).

## 4. API `/api/validation`

- POST `/sessions/{id}/start`, GET `/sessions/{id}/items`
- POST `/documents/{id}/start`, GET `/documents/{id}`
- GET `/{session_id}`, `/fields`, PATCH field
- POST `/validate`, `/reject`
- GET `/history`, `/duplicates`, `/matching`
- POST `/matches/{id}/resolve`

## 5. Permissions

`validation.read|edit|validate|reject|history|match`

## 6–7. Events / audit

Events : `validation.started.v1`, `field.edited.v1`, `field.accepted.v1`, `document.validated.v1`, `document.rejected.v1`, `duplicate.detected.v1`, `matching.completed.v1`, `ready_for_import.v1`  
Lifecycle reject audité via intake existant.

## 8. PostgreSQL

Tables : sessions, fields, history, duplicates, matches.  
Preuve : `sprint5-postgres-certification.json` → `certified: true`

## 9–11. Tests / build / routes

| Suite | Résultat |
|-------|----------|
| Sprint 5 backend | 6 PASS |
| Sprint 4 régression | 12 PASS |
| FE validationApi | 3 PASS |
| FE build | OK |
| Routes API | **388** |

## 12. Matrice

`sprint5-requirements-test-matrix.md`

## 13. Confirmations

- Aucun import exécuté  
- Aucune écriture comptable  
- Aucune création automatique client/fournisseur  
- Aucune suppression automatique de doublons  
- Pas de validation auto si erreurs / champs critiques non revus à très faible confiance  
- Historique non écrasable  

## 14. Recommandation Sprint 6

Import contrôlé depuis `ready_for_import` uniquement, avec confirmation explicite et mapping vers modules métier.

---

# SPRINT 5 CERTIFIED
