# Proposal-to-Invoice Bridge V1 (S1.6.1)

## Architecture

`ProposalInvoiceConversionService` (`app/sales_proposals/invoice_bridge.py`) orchestre la conversion.
La création de facture délègue à `create_sales_document(..., commit=False, source_*=...)`.
Aucun second modèle de facture.

## Endpoints

| Méthode | Chemin | Rôle |
|---------|--------|------|
| GET | `/api/sales/proposals/{id}/conversion-state` | État `ProposalConversionState` |
| POST | `/api/sales/proposals/{id}/conversion-preview` | Preview facture |
| POST | `/api/sales/proposals/{id}/conversion/customer` | Lien / création client |
| POST | `/api/sales/proposals/{id}/convert-to-invoice` | Conversion confirmée |

## ConversionStatus

`not_ready` | `customer_required` | `customer_ambiguous` | `ready` | `converting` | `converted` | `failed`

Distinct de `ProposalStatus`.

## Matrice d’audit (synthèse)

| Élément source | Cible | Transformation | Validation | Propriétaire | Risque | Décision |
|----------------|-------|----------------|------------|--------------|--------|----------|
| CommercialProposal accepted | Facture draft | Mapping + create_sales_document | status, blockers | Sales → Compta | Double facture | Idempotence + unique source |
| Version acceptée | source_version_id | Copie id | immuabilité | Sales | Stale version | version_id attendu |
| ProposalLine | lines_json | Map champs | totaux ±0,02 | Compta recalc | Multi-TVA | Refus si écart |
| SalesCompany | Customer | Payload explicite | org + doublons | Compta | Doublon | Sélection / force_create |
| linked_* | Bidirectionnel | FK | org | Bridge | Orphelin | Erreur contrôlée |

## Migration

- `backend/sql/elfis_proposal_invoice_bridge_s161_postgres.sql`  
- Notes SQLite : `…_sqlite.sql`  
- Tests : `Base.metadata.create_all`

## Tests

`backend/tests/sales_crm/test_proposal_invoice_bridge.py`

## Interdictions respectées

Pas d’envoi auto, pas de création silencieuse client, pas de fusion, pas de conversion hors `accepted`, pas S1.7.
