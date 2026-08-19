# Sprint 4.5 — Matrice exigences / tests

| ID | Exigence | Code | Test | Type | Résultat | Preuve | Risque résiduel |
|----|----------|------|------|------|----------|--------|-----------------|
| IDM-01 | Même fingerprint → extraction existante, pas de doublon | `service.start_extraction`, `repository.find_by_fingerprint` | `test_idempotent_retry_no_duplicate_cost`, `test_extraction_end_to_end_awaiting_validation` | unit/intégration | PASS | pytest | — |
| IDM-02 | Fingerprint avant rejet éligibilité post-validation | `service.start_extraction` (ordre) | E2E idempotence après `awaiting_validation` | intégration | PASS | pytest | — |
| IDM-03 | Changement schema/prompt/extractor → nouveau FP | `compute_input_fingerprint` | `test_fingerprint_changes` | unit | PASS | pytest | — |
| IDM-04 | Concurrent insert même FP → 1 seule active | contrainte SQL `uq_elfis_extr_active_fingerprint` + `IntegrityError` | `test_unique_active_fingerprint_constraint` | PG concurrent | PASS | pytest PG | Workers job claim : couverture partielle via job queue existante |
| IDM-05 | force_reextract supersede + scope unique | `status_scope=closed:{id}` | retry path E2E | intégration | PASS | code+pytest | Audit force_reextract non exhaustif |
| CON-01 | Deux threads insert fingerprint | SQL unique | `test_sprint45_concurrency_postgres` | PG | PASS | pytest | — |
| COST-01 | Retry idempotent ne double pas coût | `actual_cost` inchangé | `test_idempotent_retry_no_duplicate_cost` | intégration | PASS | pytest | Quotas live AI non exercés (IA off) |
| OCR-01 | OCR existant utilisé, source `ocr` | `text_resolver` | `test_ocr_existing_text_used` | unit | PASS | pytest | — |
| OCR-02 | OCR manquant → pas d’invention | `text_resolver` + service | `test_ocr_missing_no_invention`, `test_ocr_pending_no_invented_text` | unit/intégration | PASS | pytest | Job OCR auto non créé si moteur absent (voulu) |
| QUA-01 | Quarantaine / rejected / cancelled bloqués | `ExtractionEligibilityService` | `test_quarantine_and_cancelled_blocked` | unit | PASS | pytest | — |
| TEN-01 | Cross-tenant 404 | `get_extraction` | `test_cross_tenant_404` | intégration | PASS | pytest | — |
| JSON-01 | Sortie IA invalide non officielle | `validation.parse_strict_json` + adapter | `test_invalid_ai_outputs_rejected` | unit | PASS | pytest | Réparation JSON limitée (1 tentative) |
| INJ-01 | Prompt injection détectée / non exécutée | `detect_prompt_injection` | `test_prompt_injection_suite` | unit | PASS | pytest | Détection heuristique, pas exhaustive |
| PROV-01 | Provenance sans page/bbox inventées | heuristique | `test_provenance_no_invented_location` | unit | PASS | pytest | — |
| CONF-01 | Confiance non basée uniquement modèle ; human review | `compute_field_confidence`, `compute_global_confidence` | `test_confidence_not_model_only_and_human_review` | unit | PASS | pytest | — |
| FIN-01 | Tolérance 0,02 € Decimal | `check_consistency` + settings | `test_financial_tolerance_central` | unit | PASS | pytest | — |
| REC-01 | Alternatives / conflits conservés | `reconcile_fields` | `test_reconciliation_three_sources` | unit | PASS | pytest | — |
| EVT-01 | Events sans données sensibles | `safe_event_payload` | `test_redaction_and_safe_events`, E2E events | unit/intégration | PASS | pytest | — |
| LOG-01 | Redaction IBAN/email/path | `redact_text`, `assert_log_extra_safe` | `test_redaction_and_safe_events` | unit | PASS | pytest | Pas de scan CI de tous logs runtime |
| API-01 | Champs client interdits ignorés | `ExtractRequestIn` extra=ignore | `test_api_ignores_forbidden_client_fields` | unit | PASS | pytest | Tests permissions HTTP non exhaustifs 4.5 |
| FE-01 | Panel lecture seule, pas import/édition/provider | `MigrationExtractionPanel` | `MigrationExtractionPanel.test.ts` | FE | PASS | vitest | — |
| FE-02 | API client extract/list/retry | `documentExtractionApi` | `documentExtractionApi.test.ts` | FE | PASS | vitest | — |
| PG-01 | Migration staging + unicité active | SQL sprint4 | `certify_document_extraction_sprint4_5_postgres.py` | staging | PASS | `sprint4.5-postgres-certification.json` | — |
| REG-01 | Régression Analysis + Sprint4 | — | `test_pipeline.py` analysis + `test_sprint4_engine.py` | intégration | PASS | pytest | — |
| NOBIZ-01 | Aucun import métier / Sprint 5 non démarré | pipeline `import_created=False` | pipeline + panel | revue | PASS | code | — |

## Couverture volontairement partielle (risques connus)

- Quotas/réservations AI live : non facturés en mode heuristique/noop ; double facturation protégée par idempotence FP + absence d’appel IA au retry.
- Permissions HTTP matrix complète (tous rôles × endpoints) : non rejouée en 4.5 (catalog IAM branché Sprint 4).
- Deux workers job queue sur le même `extraction_id` : s’appuie sur claim job existant + unicité fingerprint ; test dédié job claim non ajouté ici.
