# 04 — Smart Library UI

## Surface

- Route : `/catalogue` (`SmartLibraryPage`)
- Nav : Tous / Produits / Services / Packs / Favoris / Récents / Plus utilisés
- Packs / Favoris / Récents / Plus utilisés : **désactivés** (capabilities false + empty honnête)
- Vues : cartes (défaut) / liste compacte
- Filtres : recherche, type, TVA, prix min/max, statut, tri, actifs seulement
- Catégorie : masquée (API absente)
- Création / édition : même formulaire UX (source opaque)
- Empty : Créer + Importer (placeholder CSV / InventoryPilot)
- Pagination client : 24 / page + cache TTL 20 s

## Perf

- Debounce recherche 220 ms
- AbortController sur reload
- Cache mémoire court par clé de filtres
- Lazy : page découpée ; pas de tableau lourd

## Style

Cartes Linear/Notion-like — tokens `--pilot-*` — pas de data-grid dense.
