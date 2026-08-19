# Sprint 6 — Matrice exigences / tests

| # | Exigence | Test / preuve | Statut |
|---|----------|---------------|--------|
| 1 | Import uniquement après validation humaine | `test_reject_non_validated_and_cross_tenant` | PASS |
| 2 | Transaction atomique (pas d’import partiel) | `test_import_transaction_complete_and_idempotent` | PASS |
| 3 | Rollback complet | `test_rollback_and_reimport` | PASS |
| 4 | Idempotence (même doc + même validation) | `test_import_transaction_complete_and_idempotent` | PASS |
| 5 | Mapping invoice.v1 → Invoice | `test_mapping_invoice_schema` | PASS |
| 6 | Liaison contact `use_existing` | `test_link_existing_contact` | PASS |
| 7 | Création contact `create_later` | `test_import_transaction_complete_and_idempotent` | PASS |
| 8 | Events complets | assertions EventNames dans tests import/rollback | PASS |
| 9 | Audit créations / liaisons / erreurs | `ElfisImportAuditLog` assertions | PASS |
| 10 | Cross-tenant → not found | `test_reject_non_validated_and_cross_tenant` | PASS |
| 11 | Permissions IAM catalog | `test_permissions_catalog` | PASS |
| 12 | Rapport versionné | `get_report` version=1 | PASS |
| 13 | PostgreSQL additive + rejeu | `certify_import_engine_sprint6_postgres.py` | PASS |
| 14 | Frontend sans delete | `importApi.test.ts` | PASS |
| 15 | Frontend build | `npm run build` | PASS |
| 16 | Régression Sprint 5 | `test_sprint5_validation.py` | PASS |
| 17 | Lifecycle transitions validées | enums + helpers lifecycle | PASS |
| 18 | Contournement Validation interdit | validators gate | PASS |

## Certification

Toutes les exigences critiques (atomique, rollback, idempotent, audit, events, PG, FE, tests) sont couvertes.

**SPRINT 6 CERTIFIED**
