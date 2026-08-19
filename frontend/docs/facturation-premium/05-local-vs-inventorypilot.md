# 05 — Local vs InventoryPilot

Référence Blueprint : Trois Lois, Zero verrou, ownership produits → Inventory.

| Mode | Comportement |
|------|----------------|
| Inventory OFF (défaut F1.0) | Catalogue `/billing/catalog` |
| Inventory ON (futur) | Même UX ; source `inventory` ; consommer capacités Inventory **sans** gérer le stock dans Compta |

## Implémentation F1.0

- Flag réel Inventory catalogue : **absent** → stub `isInventoryCatalogAvailable() === false`
- `resolveCatalogSource(inventoryEnabled)` prêt pour branchement futur
- Aucune modification InventoryPilot

## Zero verrou

Si Inventory devient indisponible → retour automatique au catalogue local (prévu ; non branché runtime).
