# 13 — Implementation report P1.0

## Livré

1. Audit runtime + matrice décisions (`01-runtime-audit.md`)
2. Contrats Smart Search génériques
3. Sources branchées : Engine V1, SharedRelations, billing customers, billingOverview, catalogue
4. UI SmartSearch (debounce, abort, cache, a11y, groupement)
5. UniversalPicker + Relation / Customer / Supplier / Document / Product
6. ProductSource + stub InventoryPilot (F1.2 prêt, non démarré)
7. Intégration Composer CustomerPicker
8. Docs README + 01–13 ; Blueprint capacités Core mises à jour
9. Tests vitest PSS + build

## Non démarré (STOP)

- F1.2 Smart Library / InventoryPilot
- Réécriture Command Center
- Index billing SalesDocument dédié
- Favoris / récents métier persistés

## Risques résiduels

- DocumentPicker billing = filtre overview (pas FTS Engine) — honnête, documenté
- GlobalSearchBar orphelin toujours présent (DEFER retrait)
- ProductsStep Composer pas encore branché sur ProductPicker UI (contrat prêt ; zéro régression produits F1.1)
