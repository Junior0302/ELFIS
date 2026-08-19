# 20 — Relations adapters

| Adapter | Source | Rôles produits |
|---------|--------|----------------|
| `customer_to_shared_relation` | `Customer` | customer |
| `contact_to_shared_relation` | `Contact` | customer / supplier / prospect selon `contact_type` |
| `sales_company_to_shared_relation` | `SalesCompany` | commercial_account |

Fichiers : `backend/app/services/shared_relations/adapters.py`

Règles :

- pas de mutation table ;
- conserver `source_system` + `source_entity_id` ;
- même contrat `SharedRelation`.
