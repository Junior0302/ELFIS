# Accounting Intelligence V2 — Matrice exigences / tests

| # | Exigence | Preuve | Statut |
|---|----------|--------|--------|
| 1 | Module `accounting_intelligence/` | Fichiers mission présents | OK |
| 2 | ContextEngine profil tenant | `context_engine.py` + retrain | OK |
| 3 | LearningEngine gated + versionné | `test_reject_and_incomplete_do_not_learn`, `memory.py` | OK |
| 4 | SimilarityEngine | `test_similarity_and_learning_feedback_accept` | OK |
| 5 | RecommendationEngine priorité 1→5 | `recommendation_engine.py` | OK |
| 6 | ExplanationEngine humain | `test_explanation_engine_human_readable` | OK |
| 7 | RuleOptimizer sans auto-modif | `test_retrain_optimizations_no_auto_rules` | OK |
| 8 | Feedback accept/modify/reject | `feedback.py` + tests | OK |
| 9 | Confidence enrichie | `confidence_engine.py` + détail API | OK |
| 10 | API intelligence | `api/routes.py` | OK |
| 11 | Frontend panel | `AccountingIntelligencePanel` | OK |
| 12 | Audit + events | `audit.py`, `events.py`, EventNames | OK |
| 13 | Isolation tenant | `test_cross_tenant_isolation` | OK |
| 14 | PostgreSQL additif | certify `certified: true` | OK |
| 15 | Pas d’écriture auto / Migration Center intact | design + scope | OK |
