# 06 — Priorités du jour

## Source

`buildDayPriorities(overview)` dans `priorities.ts`.

Signaux **uniquement** issus de `FinancialOverview` :

1. Alertes Engine (mapping sévérité → niveau)
2. KPI `factures_impayees` si value > 0
3. `documents_to_process` > 0
4. Sync banque en erreur

## Niveaux

`critical` > `high` > `normal` > `info` — max 8 items.

## Routes d’action

Dérivées du `code` d’alerte (TVA, banque, docs, factures, écritures) sinon `/finance`.

## Interdiction

Aucun montant / date / score inventé hors payload API.
