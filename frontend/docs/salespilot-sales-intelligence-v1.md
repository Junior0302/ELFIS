# SalesPilot Sales Intelligence V1 (S1.7)

## Philosophie

Priorités commerciales **déterministes** : règles lisibles, scores existants réutilisés (Health, Risk, Relationship, Proposal Readiness). Aucune IA générative. Aucune modification automatique de données.

## UX

- Dashboard : Sales Focus + 3 insights max + lien « Voir toutes les recommandations »
- Page `/sales/intelligence` — Priorités commerciales
- Détail `/sales/intelligence/:id`

## Frontière Insight / Decision

- Insights informatifs → Sales Intelligence uniquement
- Insights actionnables high/critical (tâche, deal inactif, conversion…) → peuvent créer une Decision ELFIS (`sales_insight`) + Work Queue
- Lien croisé : `linked_decision_id`

## Limites V1

- `mark-viewed` manuel → pas de signal « consultée » fiable
- Pas d’objectif commercial inventé
- Scope organisation (pas d’équipe SalesTeams)
- Notifications in-app uniquement, dédupliquées, pas d’e-mail commercial

## Suite

S1.8 Operations & Productivity : voir `salespilot-operations-v1.md` / `sales-operations-v1.md`.
