# Rapport Phase C — Documents, Vault, DI, OCR, AI, Accounting

Date : 2026-07-20  
Environnement : `ELFIS_ENVIRONMENT=test` · stockage Vault mock · OpenAI/OCR off  
Commande : `python scripts/run_functional_validation.py --phase-c`  
Commit / push : **aucun**

---

## 1. Cartographie pipeline

```
Upload PDF → validate_uploaded_file → Vault archive (+ hash)
  → event vault.document.archived.v1
  → job extract_text
  → document.extraction.completed.v1
  → job AI classification / extraction / quality
  → document.analysis.completed.v1
  → job accounting.build_proposal
  → proposition (ready_for_validation | requires_review)
  → notifications / search (handlers existants)
```

| Étape | Emplacement |
|-------|-------------|
| Upload | `POST /api/vault/documents/archive` |
| Validation fichier | `security_file_validation.validate_uploaded_file` |
| Vault | `vault_service.archive_document` |
| Events | `document_intelligence.event_handlers`, `ai`, `accounting` |
| Jobs | `jobs/handlers/document_intelligence_handlers`, `ai_handlers`, `accounting_handlers` |
| Finance | `financial_validation_stage` (tolérance Decimal `elfis_accounting_amount_tolerance`, défaut **0.02**) |
| Mapping | `accounting/stages` + `map_accounting` |
| Legacy upload | `POST /api/documents/upload` — pipeline agents sync, hors Vault (documenté) |

---

## 2. Routes auditées

- Vault archive / list / get  
- DI extract-text / text-extraction  
- AI analyze  
- Accounting proposals validate / reject  
- Legacy `/api/documents/upload` (pas de quotas Vault — écart connu, hors correction majeure)

---

## 3. Types & fixtures

Types : supplier_invoice, customer_invoice, credit_note, quote, receipt (review si hors V1 accounting).  
Fixtures : `tests/functional/fixtures/generate_documents.py` (PDF synthétiques).

---

## 4. Stratégie OCR

`ELFIS_OCR_ENABLED=false` par défaut → provider disabled.  
Scan / texte vide → `requires_ocr` ; job OCR → failed/dead_letter contrôlé.  
MockOCRProvider préparé, non branché runtime V1.

---

## 5. Politique doublons Vault

**Route archive** : même checksum org → **HTTP 409** + `existing_document_id` (pas de second blob).  
**Delivery** : `archive_or_reuse_pdf` peut publier `vault.document.reused.v1`.

---

## 6. Anomalies

### PHC-C-001 — Archive Vault ne démarrait pas le pipeline

| Champ | Valeur |
|-------|--------|
| **ID** | PHC-C-001 |
| **Sévérité** | CRITICAL |
| **Cause** | `archive_document` n’émettait pas `vault.document.archived.v1` (seul delivery le faisait) |
| **Correction** | Publication `safe_publish` après archive réussie (`vault_service.py`) |
| **Test** | `test_vault_001_002_archive_unique_hash` |
| **Résultat** | PASS |

### PHC-C-002 — Event sans commit perdu en tests

| Sévérité | MINOR |
| Correction | `commit=True` sur publish archive |
| Résultat | PASS |

---

## 7. Fichiers

**Créés** : 14 scénarios `test_phase_c_*.py`, `helpers/phase_c.py`, ce rapport.  
**Modifiés** : `vault_service.py`, `conftest.py` (mock storage + rate limit off), `run_functional_validation.py` (`--phase-c`), checklist, how-to.

---

## 8. Résultats

| Suite | Résultat |
|-------|----------|
| Phase C scenarios | **43 passed** |
| vault + DI + AI + accounting | **118 passed** |
| FastAPI | **OK** (240 routes) |
| Frontend build | **OK** |
| Appels AI/OCR réseau | **0** |
| Issues documentaires critiques restantes | **0** |

---

## 9. Notifications

Implémentées (handlers) : vault archived, analyse, revue, proposition.  
Absentes / partielles en V1 : certaines variantes OCR/quota (documentées hors auto).

---

## 10. Limites & manuels

- Chaîne E2E heuristique sans OpenAI : classification approximative  
- Éditeur de lignes comptables non V1  
- Legacy `/documents/upload` sans quotas Vault  
- UI : checklist PHASE C manuelle (25 scénarios)

---

## 11. Matrice PASS

```
File validation................ PASS
Vault archive.................. PASS
Vault deduplication............ PASS
Text extraction................ PASS
OCR decision................... PASS
OCR mock pipeline.............. PASS
AI classification.............. PASS
Structured extraction.......... PASS
Quality checks................. PASS
Financial validation........... PASS
Accounting mapping............. PASS
Balanced proposals............. PASS
Human review................... PASS
Retries........................ PASS
Idempotency.................... PASS
Entitlements / quotas.......... PASS
Tenant isolation............... PASS
Search / notifications......... PASS
Security / observability....... PASS

Phase C functional tests........ 43 passed
Regression tests............... 118 passed
FastAPI import................. OK
Frontend build................. OK
Real AI/OCR calls.............. 0
Known critical document issues. 0
```
