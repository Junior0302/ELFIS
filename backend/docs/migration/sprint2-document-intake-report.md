# Document Intake Engine V1 — Rapport Sprint 2

Date : 2026-07-23  
Module : `document_intake` (ELFIS Core, réutilisable)  
Verdict : **SPRINT 2 LIVRÉ** (tests verts, build OK)

---

## 1. Architecture

Module indépendant sous `backend/app/document_intake/` :

| Fichier | Rôle |
|---------|------|
| `format_registry.py` | Formats acceptés (extensible) |
| `validators.py` | Extension, MIME réel, nom, double ext, vide |
| `checksum.py` | SHA-256 |
| `scanner.py` | Stub antivirus (architecture) |
| `storage.py` | Stockage **temporaire** local (`storage/document_intake/`) |
| `inventory.py` | Agrégats inventaire |
| `models.py` / `repository.py` / `service.py` | Inventaire + métier |
| `events.py` | Event Bus |
| `api/routes.py` | HTTP uniquement (pas de logique) |

Aucune logique OCR / IA / extraction / import comptable.

---

## 2. Tables

`elfis_document_intake_items` — SQL : `backend/sql/elfis_document_intake_postgres.sql`  
Enregistré dans `SQL_ORDER` + `EXPECTED_TABLE_FAMILIES`.

Champs clés : UUID, `intake_token`, `organization_id`, `migration_session_id`, checksum, mime, taille, noms, `relative_path`, statut, origine, `storage_key`, flags doublon/quarantaine.

---

## 3. Statuts

`uploaded` → `validated` / `quarantined` / `duplicate` → `ready_for_analysis` (si non-ZIP)  
ZIP : `validated` + `extract_later=true` (pas d’extraction)  
`rejected` / `cancelled`

---

## 4. API (`/api/document-intake`)

| Méthode | Chemin | Permission |
|---------|--------|------------|
| GET | `/formats` | `document_intake.read` |
| GET | `/items` | `document_intake.read` |
| GET | `/items/{id}` | `document_intake.read` |
| POST | `/uploads` | `document_intake.upload` |
| POST | `/uploads/batch` | `document_intake.upload` |
| POST | `/items/{id}/cancel` | `document_intake.cancel` |

Isolation org + 404 cross-tenant. Lien optionnel `migration_session_id`.

---

## 5. Événements

- `document.uploaded.v1`
- `document.validated.v1`
- `document.rejected.v1`
- `document.duplicate_detected.v1`
- `document.ready_for_analysis.v1`

Payload sans contenu fichier / secrets.

---

## 6. Frontend

- `documentIntakeApi.ts` + tests
- `MigrationIntakePanel.tsx` : drag & drop, fichiers/dossier, progression transfert, liste, statuts, doublons, annulation
- Intégré au wizard migration lorsque `status === awaiting_upload`

---

## 7. Tests & build

| Suite | Résultat |
|-------|----------|
| `tests/document_intake` | **10 passed** |
| Frontend vitest (intake + migration) | **14 passed** |
| `npm run build` | **OK** |
| Routes FastAPI | **351** (+6 vs Stage 2 certifié 345) |

---

## 8. Limites

- Antivirus réel : stub uniquement
- Stockage temporaire local (pas d’archivage vault définitif)
- ZIP inventorié, non extrait
- Quotas soft module (batch/session/org) — billing enforce optionnel plus tard
- Pas d’OCR / IA / mapping / import

---

## 9. Prochain sprint (recommandé)

1. Extraction ZIP asynchrone (Job Queue)
2. Pipeline analyse (classification légère sans IA générative si besoin)
3. Promotion storage → Document Registry / quarantine provider
4. Timeline migration `file_upload` → `analysis`
5. Prévisualisation PDF/images

---

## 10. Confirmation hors périmètre

**Aucun** OCR, IA, extraction métier, classification intelligente, import comptable, mapping, rapprochement bancaire, création clients/fournisseurs.
