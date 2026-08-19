# Sprint 7 — Matrice exigences / tests

| # | Exigence | Test / preuve | Statut |
|---|----------|---------------|--------|
| 1 | Orchestration sans remplacer pipelines | `orchestrator.py` délègue `ImportEngineService` | PASS |
| 2 | Batch 100 documents | `test_batch_manager_100_and_1000_simulated` | PASS |
| 3 | Batch 1000 simulés | idem | PASS |
| 4 | Resume | `test_resume_cancel_retry_dashboard_report` | PASS |
| 5 | Cancel | idem | PASS |
| 6 | Dashboard | idem | PASS |
| 7 | Report | idem | PASS |
| 8 | Cleanup | `test_cleanup_requires_confirmation` | PASS |
| 9 | Progress serveur | `test_progress_never_client_side` | PASS |
| 10 | Permissions | `test_permissions_catalog` | PASS |
| 11 | PostgreSQL | `sprint7-postgres-certification.json` | PASS |
| 12 | Frontend | `smartMigrationApi.test.ts` + build | PASS |
| 13 | Régression S5–S6 | 18 tests verts | PASS |

**SPRINT 7 CERTIFIED** — inclus dans **MIGRATION CENTER V1 CERTIFIED**
