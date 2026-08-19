# 05 — Relation / Customer / Supplier pickers

## RelationPicker

- Recherche SharedRelation (`list` / `search`)
- Sélection → `SearchResult` id opaque (`customer:N`, …)
- Lien « Ouvrir ELFIS Relations »
- Create optionnel (parent)

## CustomerPicker

Spécialisation RelationPicker + :

1. Dual source : relations customer + `listCustomers` (fallback zéro régression)
2. Mapping → `{ customerId, relationId, displayName, email, …, source }`
3. Création via `api.createCustomer` (workflow billing existant)

**Document Composer** (`/facturation/nouveau`) : `ClientStep` délègue à `CustomerPicker`.

## SupplierPicker

Filtre rôle `supplier` uniquement.
