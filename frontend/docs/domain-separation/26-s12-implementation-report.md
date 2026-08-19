# 26 — S1.2 implementation report

## Modèles audités

customers, contacts, sales_companies (+ people/org/members documentés en 18)

## Contrat

`SharedRelation` + opaque IDs `source:id`

## Adapters

customer / contact / sales_company → même contrat

## Endpoints

`/api/shared/relations*` lecture seule, isolation org, audit

## UI

`/platform/relations` + détail `/:id` ; liens Compta/Sales

## Doublons

Détection non destructive ; `auto_merge: false`

## Permissions

Mapping temporaire sur permissions existantes

## Limites

- Pas de table Party
- Pas d’index Search Engine dédié (Command Center nav only)
- Création toujours via formulaires source
- Partenaires quasi absents en données réelles

## Tests / build

- Unitaires backend : **OK** (`test_shared_relations_s12.py`)
- IDs frontend : **OK**
- `tsc -b && vite build` : **OK**

## GO / NO GO

**GO conditionnel** — contrat + adapters + API + UI lecture ; validation manuelle R01–R20 restante.

## Dette S1.3

- Table parties
- Permissions platform.relations.*
- Index search unifié anti-doublon résultats
- Fusion manuelle guidée
- Remplacement progressif formulaires création

**STOP — S1.3 non commencé.**
