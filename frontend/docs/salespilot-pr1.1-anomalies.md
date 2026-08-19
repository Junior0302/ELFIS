# SalesPilot PR1.1 — rapport d’anomalies

Collecte durant la recette d’intégration V1. Les items **bloquants** sont corrigés dans PR1.1.

| ID | Gravité | Surface | Étapes | Attendu | Réel | Correction | Test |
|----|---------|---------|--------|---------|------|------------|------|
| A-01 | Critique | Bridge TVA | Convertir proposition multi-taux | Refus explicite | Avant : taux 1ʳᵉ ligne silencieux | Option B : blocker preview + 409 `multi_vat_unsupported` | `test_multi_vat_blocked_on_preview_and_convert` |
| A-02 | Majeur | Ops | Nav « Reports » | Page réelle ou absente | Stub `SalesEmptyPage` | Retiré de la sidebar (route conservée hors nav) | `sales-shell.test.ts` |
| A-03 | Majeur | Pipeline défaut | Activation org | Pipeline 7 étapes | Uniquement au 1er accès API | `ensure_default_pipeline` dans provisioning workspace | provisioning + `defaults.py` |
| A-04 | Majeur | Recette | Données demo | Seed local | Absent | `scripts.seed_salespilot_demo` | seed manuel |
| A-05 | Mineur | Nav | Ordre FR | Ordre PR1.1 | Ordre partiel | `salesNavModel.ts` réordonné | shell tests |
| A-06 | Info | E2E | Playwright | Parcours auto | Non présent dans le repo | Procédure manuelle + smoke API ; pas d’ajout Playwright PR1.1 | manual-test-v1 |
| A-07 | Mineur | Migrations | Postgres persistant | DDL S1.6–S1.9 | SQL CRM documentaire only | `apply_salespilot_migrations` + create_all | `--report-only` |
| A-09 | Mineur | Intelligence sync | Seed + Decision Center | Sync crée insights | SQLite manquait colonnes exécution Decision Center | Colonnes ajoutées dans `init_db` SQLite | seed `insights_sync.created=14` |

## Non corrigé (dette restante)

- Support réel TVA multi-taux côté ComptaPilot (Option A) — hors scope PR1.1
- Page Reports SalesPilot — phase ultérieure
- Couverture E2E Playwright complète — PR ultérieure
- UI membres d’équipe : minimale mais testable ; enrichissement UX hors PR1.1
