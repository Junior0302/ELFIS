# 05 — Catalogue

## Source

| Source | Statut F1.1 |
|--------|-------------|
| Catalogue local ComptaPilot | Branché (`api.listCatalog` / `createCatalogItem`) |
| Derniers | Slice des 8 premiers (proxy honnête) |
| Favoris / Plus vendus | Empty honnête (données non exposées) |
| InventoryPilot | Stub `isInventoryCatalogAvailable() === false` |

## Lignes

Éditeur : produit, qté, prix, TVA, remise %, total ligne.

Actions : Dupliquer / Supprimer / Monter / Descendre / Ajouter dessous.

## DnD

**Non branché** — aucune lib drag-and-drop dans le frontend. Réordonnancement via boutons. Reporté F1.2 si lib approuvée.
