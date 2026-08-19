# Migration Center V1 — Matrice de certification globale

| Sprint | Module | Exigence clé | Preuve | Statut |
|--------|--------|--------------|--------|--------|
| 1 | migration_center | Sessions / profil / sources | Routes `/api/migrations`, wizard | PASS |
| 2 | document_intake | Intake de base | Module + tests historiques | PASS |
| 2.5 | document_intake | Universal ID, lifecycle, upload | Cert PG stage2.5 | PASS |
| 3 | document_analysis | Pipeline analyse | Cert PG sprint3 | PASS |
| 4 | document_extraction | Extraction IA | Cert PG sprint4 | PASS |
| 4.5 | document_extraction | Durcissement | Cert PG sprint4.5 | PASS |
| 5 | validation_mapping | Validation humaine | `test_sprint5_validation.py` 6 PASS | PASS |
| 6 | import_engine | Import transactionnel | `test_sprint6_import.py` 6 PASS | PASS |
| 7 | smart_migration | Orchestration Enterprise | `test_sprint7_smart_migration.py` 6 PASS | PASS |

## Contrôles transverses Sprint 7

| # | Exigence | Test | Statut |
|---|----------|------|--------|
| 1 | Ne pas modifier pipelines S1–S6 | Revue code + régression 18 PASS | PASS |
| 2 | Batch configurable | 100 docs / 4 lots ; 1000 / 20 lots | PASS |
| 3 | Resume sans retraiter terminés | `test_resume_cancel_retry_dashboard_report` | PASS |
| 4 | Cancel | idem | PASS |
| 5 | retry_failed | API + service | PASS |
| 6 | Dashboard serveur | ProgressEngine + Dashboard | PASS |
| 7 | Report JSON/CSV/PDF | ReportingService | PASS |
| 8 | Cleanup confirmation | `test_cleanup_requires_confirmation` | PASS |
| 9 | Métriques / coûts | metrics collect | PASS |
| 10 | Events | SMART_MIGRATION_* | PASS |
| 11 | PostgreSQL additive | certify sprint7 | PASS |
| 12 | Frontend build | `npm run build` | PASS |
| 13 | Routes totales | 405 | PASS |

## Certification

Aucun sprint ne régresse. Couche Enterprise opérationnelle.

**MIGRATION CENTER V1 CERTIFIED**
