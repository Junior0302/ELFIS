# Accounting Engine V2 — Matrice exigences / tests

| # | Exigence | Preuve | Statut |
|---|----------|--------|--------|
| 1 | Module `accounting_engine/` complet | Fichiers `engine`, `proposal_service`, resolvers, engines, learning, events, audit | OK |
| 2 | Pipeline sans écriture définitive | `AccountingEngine.generate` + disclaimer proposition | OK |
| 3 | AccountResolver multi-plans + priorité | `account_resolver.py` + PCG défaut | OK |
| 4 | VATEngine HT/TVA/TTC + anomalies | `test_vat_engine_and_exempt` | OK |
| 5 | JournalResolver ACH/VTE/… | `test_purchase_invoice_proposal`, `test_sales_invoice_and_credit_note` | OK |
| 6 | ConsistencyEngine | `test_no_vat_and_multi_line_consistency` | OK |
| 7 | ConfidenceEngine | `test_regenerate_confidence_explanation_learning` | OK |
| 8 | Proposition V2 (journal, lignes, TVA, score, warnings, explications) | generate + schemas API | OK |
| 9 | LearningEngine sans rules globales | `remember_validation` + lookup | OK |
| 10 | API GET/POST generate/regenerate/confidence/explanation | `api/routes.py` | OK |
| 11 | Frontend AccountingProposalPanel | composant + page + nav | OK |
| 12 | Tests achat/vente/TVA/avoir/tenant/permissions | suite pytest 7 PASS | OK |
| 13 | Migration PostgreSQL additive | SQL + certify `certified: true` | OK |
| 14 | IAM `accounting_engine.*` | catalog + `test_cross_tenant_and_permissions_catalog` | OK |
| 15 | Pas de Migration Center touché | hors scope cette phase | OK |
