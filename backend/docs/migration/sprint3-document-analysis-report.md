# Document Analysis Pipeline V1 — Sprint 3 Certification Report

**Date:** 2026-07-23  
**Verdict:** **SPRINT 3 CERTIFIED**

## Architecture

Module indépendant `backend/app/document_analysis/` :

| Zone | Contenu |
|------|---------|
| `pipeline.py` | 12 étapes séquentielles indépendantes |
| `analyzers/` | technique, décision OCR |
| `metadata/`, `pages/`, `orientation/`, `quality/`, `language/` | étapes dédiées |
| `classifiers/` | heuristiques (invoice, quote, …) |
| `service.py` | orchestration + lifecycle + storage |
| `api/routes.py` | HTTP sans logique métier |
| `models.py` | `elfis_document_analysis_reports` |

Aucun LLM. Aucune extraction métier. OCR **décidé** mais **jamais exécuté**.

## Pipeline

1. Upload terminé → 2. Validation OK → 3. Métadonnées → 4. Technique → 5. Format réel → 6. Pages → 7. Orientation → 8. Qualité → 9. Langue → 10. OCR ? → 11. Classification → 12. Ready for AI

Rapport JSON versionné (`schema_version=1`, `analysis_version=1.0.0`) avec `llm_used=false`, `ocr_executed=false`, `extraction=null`.

## Lifecycle

```
ready_for_analysis → analysis_pending → analyzing → classified → ready_for_ai
```

Statut `ready_for_ai` ajouté. Quarantaine / rejeté / annulé : analyse refusée.

## API

| Méthode | Chemin | Permission |
|---------|--------|------------|
| POST | `/api/document-analysis/items/{id}/analyze` | `document_analysis.run` |
| POST | `/api/document-analysis/sessions/{id}/analyze` | `document_analysis.run` |
| GET | `/api/document-analysis/reports/{id}` | `document_analysis.read` |
| GET | `/api/document-analysis/items/{id}/report` | `document_analysis.read` |
| GET | `/api/document-analysis/sessions/{id}/reports` | `document_analysis.read` |

## Events

- `document.analysis.started.v1`
- `document.analysis.completed.v1`
- `document.analysis.failed.v1`
- `document.analysis.ready_for_ai.v1`

## Frontend

- `MigrationAnalysisPanel` — qualité, langue, orientation, type, OCR, progression, avertissements
- Wizard étape **Analyse** (step 4) débloquée

## Tests

| Suite | Résultat |
|-------|----------|
| `tests/document_analysis` + `tests/document_intake` | **34 passed** |
| Vitest analysis + intake | **10 passed** |
| `npm run build` | OK |
| PostgreSQL staging Sprint 3 | **certified: true** (apply + idempotent) |

## Routes

**364** (+5 vs Sprint 2.5 à 359).

## Performances

Pipeline synchrone léger (pypdf + Pillow). Temps typique < 1 s / fichier de test. Pas de worker async dans cette passe (acceptable V1).

## Limites

- Classification heuristique uniquement (pas d’IA)
- Langue basée sur stopwords + texte extractible
- Orientation PDF via `/Rotate` / EXIF image — pas de correction
- Pas d’OCR réel, pas d’extraction, pas d’import
- ZIP inventorié, non extrait

## Prochain sprint (recommandé)

Sprint 4 — OCR Engine : consommer `need_ocr=true` + `ready_for_ai`, Job Queue, sans extraction comptable.

---

**SPRINT 3 CERTIFIED**
