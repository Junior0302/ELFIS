# 19 — Shared Relations contract

## Party conceptuel

- `person` | `organization`
- Rôles : customer, supplier, prospect, partner, employee, commercial_account, billing_contact

## SharedRelation (canonique)

Voir `backend/app/services/shared_relations/contract.py`

Champs : id, organization_id, party_type, display_name, legal_name, first/last name, emails[], phones[], addresses[], tax_number, siren, siret, roles[], status, source_system, source_entity_id, timestamps, links.

## Propriété

| Domaine | Possède |
|---------|---------|
| ELFIS Core | Identité, coordonnées, légaux, rôles, statut global (projection) |
| SalesPilot | Pipeline, owner, opportunités, activités, score |
| ComptaPilot | Paiement, fiscalité métier, factures, solde, écritures |

## ID stable (transitoire)

`{source_system}:{source_entity_id}`  
Ex. `customer:123`, `contact:98`, `sales_company:42`

Migration future → `party_id` UUID / table parties (S1.3+).
