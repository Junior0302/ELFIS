# 07 — Local Library

`localLibrarySource` :

- `list` / `search` → `api.listCatalog` + filtres / tri / pagination mémoire
- `create` / `update` / `delete` → endpoints billing
- `duplicate` → create avec suffixe « (copie) »
- capabilities : history / favorites / recents / mostUsed / import / packs = **false**

Ownership données : tables `catalog_items` (billing ComptaPilot) — Loi 3 respectée jusqu’au basculement Inventory.
