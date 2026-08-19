# 08 — Inventory ready (Blueprint)

## Remplacement prévu

1. Implémenter `inventoryPilotResourceSource` (`available: true`) sur API Inventory (ownership Inventory).
2. Activer résolution : `resolveResourceSource('inventory_pilot')` quand Pilot actif.
3. `ProductSource` / ProductPicker / Smart Library **inchangés** côté UX (même `Resource` / mêmes cards).
4. Migration auto des références `catalogItemId` → ids Inventory via projection / intents plateforme.
5. **Zero ressaisie** : pas de re-saisie prix / TVA / libellés si projection fournie.
6. ComptaPilot continue de **consommer** la capacité catalogue — ne gère pas stocks / entrepôts / fournisseurs.

## Ce qui ne change pas pour l’utilisateur

- Même Smart Library
- Même ProductPicker
- Même formulaire création (owner technique opaque)
- Empty / favoris restent honnêtes jusqu’à exposition réelle

## Interdit en F1.2

Créer InventoryPilot, stocks, fournisseurs, entrepôts, ou inventer des données.
