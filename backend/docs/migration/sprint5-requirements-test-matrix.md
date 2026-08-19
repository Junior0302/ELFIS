# Sprint 5 — Matrice exigences / tests

| ID | Exigence | Code | Test | Résultat |
|----|----------|------|------|----------|
| LIF-01 | awaiting_validation → human_validating → validated_by_user → ready_for_import | `enums` + `lifecycle_service` | `test_validation_edit_history_and_ready_for_import` | PASS |
| LIF-02 | Rejet depuis validation | `mark_rejected` | `test_reject_and_cross_tenant` | PASS |
| EDIT-01 | Édition non destructive + user_corrected | `edit_field` | E2E edit | PASS |
| HIST-01 | Historique append-only | `history.append_history` | E2E history | PASS |
| VAL-01 | Erreurs montants bloquent validation | `validators` + `validate_document` | `test_no_auto_validate_with_amount_errors` | PASS |
| VAL-02 | Pas d’auto-accept basse confiance | `validate_document` critical check | code + test amounts | PASS |
| DUP-01 | Doublons proposés seulement | `duplicates.detect_document_duplicates` | start_or_get | PASS |
| MATCH-01 | Matching sans création | `matcher.match_party` | start_or_get | PASS |
| EVT-01 | Events validation.* | `events.py` | E2E event names | PASS |
| TEN-01 | Cross-tenant 404 | `get_session` | `test_reject_and_cross_tenant` | PASS |
| IDM-01 | Start idempotent | `start_or_get` | `test_idempotent_start_session` | PASS |
| API-01 | Permissions validation.* | IAM catalog/map | wiring | PASS |
| FE-01 | Panel + API client | `MigrationValidationPanel`, `validationApi` | vitest | PASS |
| FE-02 | Aucun bouton Import | panel | revue code | PASS |
| PG-01 | Migration staging | SQL sprint5 | `sprint5-postgres-certification.json` | PASS |
| NOIMP-01 | Aucun import métier | service / pipeline flags | revue | PASS |
