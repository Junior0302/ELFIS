# Sprint 4 — AI Extraction Engine V1 — Rapport de certification

**Date :** 2026-07-23  
**Module :** `document_extraction` (ELFIS Core)  
**Verdict :** **SPRINT 4 CERTIFIED**

---

## 1. Architecture

Module indépendant `app/document_extraction` branché sur Document Intake + Document Analysis. Pipeline versionné multi-stratégie (structuré → heuristique → LLM adapter → fallback). Résultat = proposition en `awaiting_human_validation` / lifecycle document `awaiting_validation`. **Aucun import métier.**

## 2. Fichiers créés

| Zone | Fichiers |
|------|----------|
| Module | `models.py`, `schemas.py`, `service.py`, `pipeline.py`, `eligibility.py`, `text_resolver.py`, `normalization.py`, `events.py`, `exceptions.py`, `enums.py`, `repository.py`, `document_types/`, `extractors/`, `providers/`, `quality/`, `api/` |
| Jobs | `jobs/handlers/document_extraction_handlers.py` |
| SQL | `sql/elfis_document_extraction_sprint4_postgres.sql` |
| Cert | `scripts/migration/certify_document_extraction_sprint4_postgres.py` |
| Tests BE | `tests/document_extraction/test_sprint4_engine.py` |
| FE | `MigrationExtractionPanel.tsx`, `documentExtractionApi.ts`, `documentExtractionApi.test.ts` |
| Docs | ce rapport |

## 3. Fichiers modifiés

- `main.py` — router `/api/document-extraction`
- `iam/permission_catalog.py`, `iam/role_permission_map.py`
- `jobs/job_types.py`, `jobs/__init__.py`
- `events/event_types.py` (événements extraction)
- `document_intake/enums.py` + `lifecycle_service.py` (transitions extraction/OCR)
- `scripts/rc1/migrate_sql.py` (SQL_ORDER)
- `frontend/.../MigrationWizardPage.tsx` (étape Extraction)

## 4. Schémas d’extraction

`invoice.v1`, `quote.v1`, `credit_note.v1`, `receipt.v1`, `bank_statement.v1`, `contract.v1`, `generic_document.v1` — registry `document_types/`.

## 5. Pipeline

Étapes + progression : eligibility 5 % → text 15 % → schema 20 % → heuristic 35 % → AI 60 % → norm 72 % → reconcile 82 % → validation 90 % → confidence 96 % → completed 100 %.

## 6. Stratégies

`structured` | `heuristic` | `llm` | `heuristic_plus_llm` | `fallback` via sélecteur implicite du pipeline.

## 7. Providers

Adapter `ExistingAIProviderAdapter` sur `AIService` existant (`DOCUMENT_EXTRACTION_AI_PROVIDER=existing_default`). No-op si IA désactivée → heuristique seule.

## 8. Prompt injection

Texte traité comme donnée ; détection motifs (`IGNORE_INSTRUCTIONS`, `REVEAL_PROMPT`, etc.) → warning `prompt_injection_detected` ; pas d’exécution d’outils.

## 9. Normalisation

Dates ISO, montants Decimal/float, devises ISO, IBAN masqué (`iban_masked`), raw conservé dans meta.

## 10. Réconciliation

`reconcile_fields` : confirmed / selected / conflicted + alternatives.

## 11. Confiance

Champ par champ + score global pondéré ; `requires_human_review=True` toujours (Migration Center).

## 12. Provenance

Par champ : source, extractor, confidence, page/bbox null si inconnus.

## 13. Cohérence

Tolérance financière **0,02 €** (settings ou `AMOUNT_TOLERANCE`).

## 14. Lifecycle

`ready_for_ai` → `extraction_pending` → `extracting` → `extracted` → `awaiting_validation` ; OCR manquant → `ocr_pending` (sans inventer de texte).

## 15–16. Tables / migration PG

- `elfis_document_extractions`
- `elfis_document_extraction_attempts`
- Unicité `(organization_id, input_fingerprint, status_scope)`
- Staging certifié : scénarios A/B/C OK (`certified: true`)

## 17–18. Endpoints / permissions

`/api/document-extraction` : extract, list, get, status, fields, warnings, provenance, retry, cancel, session extract/list.

Permissions : `document_extraction.read|run|retry|cancel|view_sensitive`.

## 19. Job Queue

`document.extraction.run.v1` → `DocumentExtractionRunJobHandler`.

## 20. Quotas

Réutilisation du chemin AI Engine ; refus propre `QUOTA_EXCEEDED` (429) prévu côté API. Limites commerciales non hardcodées dans les routes.

## 21–23. Events / audit / observabilité

Events `document.extraction.*.v1` (payload métadonnées sûres uniquement). Logs structurés sans texte brut / IBAN complet.

## 24–25. Tests

| Suite | Résultat |
|-------|----------|
| `test_sprint4_engine.py` | **12 passed** |
| `test_pipeline.py` (analyse) | **9 passed** (régression) |
| FE `documentExtractionApi.test.ts` | **3 passed** |
| FE build | **OK** |
| PG staging Sprint 4 | **certified: true** |

## 26. Matrice exigences / tests (critique)

| Exigence | Couverture |
|----------|------------|
| Éligibilité / quarantaine | `test_eligibility_quarantine_and_ready` |
| Text resolver / OCR | `test_text_resolver_*`, `test_ocr_pending_*` |
| Schémas | `test_schemas_registered` |
| Heuristique + human review | `test_pipeline_heuristic_*`, E2E |
| Normalisation | `test_normalization_*` |
| Cohérence 0,02 | `test_consistency_tolerance` |
| Réconciliation | `test_reconciliation_*` |
| Idempotence fingerprint | E2E + `test_fingerprint_*` |
| Prompt injection | `test_prompt_injection_*` |
| Cross-tenant 404 | `test_cross_tenant_404` |
| Events non sensibles | E2E payload check |
| Pas d’import métier | `import_created is False` |
| FE pas d’édition/import | panel lecture seule |
| PG staging | cert script |

## 27–28. Build / routes

- Frontend build : OK  
- **Total routes API : 375** (dont 11 sous `/api/document-extraction` + 2 platform legacy document-processing)

## 29–31. Perf / limites / coûts

Traitement sync par défaut sur lancement UI ; job async disponible. Limites : `MAX_TEXT_CHARACTERS=50000`, max pages PDF 100. Coût LLM = 0 en mode heuristique/noop.

## 32. Confirmation anti-import

Aucun client, fournisseur, produit, écriture, rapprochement, archive définitive, ou validation auto. Frontend : pas de choix provider/modèle, pas d’édition finale, pas de bouton import.

## 33. Recommandation Sprint 5

Validation humaine : édition champs, corrections `user_corrected`, confirmation/rejet, passage vers import contrôlé (sans création métier automatique non validée).

---

## Critères de certification — checklist

- [x] Tests précédents + extraction verts  
- [x] Build frontend OK  
- [x] PostgreSQL staging certifié  
- [x] Sorties structurées versionnées + provenance/confiance  
- [x] Tolérance 0,02 €  
- [x] Idempotence fingerprint  
- [x] Prompt injection traité  
- [x] Events sans contenu sensible  
- [x] Quarantaine bloquée / OCR non inventé  
- [x] Aucun import métier  
- [x] `awaiting_validation` / `awaiting_human_validation`  
- [x] Matrice de traçabilité présente  

---

# SPRINT 4 CERTIFIED
