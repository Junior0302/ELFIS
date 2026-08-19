# Sales Intelligence Architecture V1 (S1.7)

## Module

`backend/app/sales_intelligence/`

- Règles : `rules.py` (seuils documentés dans `priorities.py`)
- Persistance : `SalesInsightItem` (déduplication `organization_id + deduplication_key`)
- Service : sync ciblé, focus, overview, acknowledge, dismiss
- Endpoints : `/api/sales/intelligence*`

## Méthode pipeline

Seuils **absolus documentés** (pas d’objectif fictif) :

- Congestion étape ≥ 8 opportunités
- Sans next action ≥ 5
- Part risque high/critical ≥ 35 %

## Requêtes approximatives par sync

1. opportunités ouvertes (≤120)
2. stages liés
3. activités récentes (≤200)
4. tâches actives (≤80)
5. propositions (≤80)
6. upserts insights + résolution stale
7. décisions/notifications ciblées

Pas de scan multi-org. Pas de N+1 activité par deal (index en mémoire).

## Scores réutilisés

- `health_score_for` / `risk_level_for` / `days_in_stage` (pipeline_service)
- Proposal readiness persistée
- Conversion status (S1.6.1)

## Migration

`backend/sql/elfis_sales_intelligence_s17_postgres.sql`

## Interdictions

Pas d’IA générative, pas d’e-mail auto, pas de changement pipeline/probabilité auto, pas S1.8.
