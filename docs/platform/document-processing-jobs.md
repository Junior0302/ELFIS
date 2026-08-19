# Document Processing Jobs

## API

Préfixe : `/api/document-processing`

- `POST /jobs` — créer
- `GET /jobs` — lister (pagination, filtres)
- `GET /jobs/{id}` — détail
- `GET /jobs/{id}/steps`
- `GET /jobs/{id}/attempts`
- `POST /jobs/{id}/cancel`
- `POST /jobs/{id}/retry`

Tri stable : `created_at DESC, id DESC`. Isolation tenant obligatoire.

## Statuts job

`pending` · `queued` · `running` · `retrying` · `completed` · `partially_completed` · `failed` · `cancelled` · `timed_out` · `blocked`

Transitions contrôlées (ex. `completed → running` interdit).

## Idempotence

`(organization_id, idempotency_key)` — réutilisation retourne le job existant sans recréer les étapes.

## Version documentaire

Le job pointe une `document_version_id` précise ; une nouvelle version courante n’altère pas le job en cours.

## IAM

- `document_processing.jobs.read|create|cancel|retry|manage`
- `document_processing.pipelines.read`
- `document_processing.workers.read|manage`

## Audit

Actions `DOCUMENT_PROCESSING_*` — métadonnées bornées (ids, codes, durée). Pas de contenu documentaire, OCR, secrets ni stack traces.

## Health

Provider `document_processing` : queued, running, failed 1h, oldest queued age, leases expirées.

## OCR (RC2.5.3)

Pipelines : `document_ocr_v1` via `POST /jobs` avec `pipeline_key`.
Résultats : `/ocr-results`, `/ocr-results/{id}/pages`, `/ocr-results/{id}/text`, retry/reject.
Providers publics : `/ocr/providers`.
Permissions `document_processing.ocr.*` — le texte n’est jamais dans les listes.
