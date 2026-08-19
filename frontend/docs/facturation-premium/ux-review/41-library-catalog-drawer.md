# 41 — LibraryCatalogModal (ex-drawer) — F1.3.2.2

## Statut

**Drawer latéral remplacé** par sous-modale centrée `LibraryCatalogModal`.

## Rôle

Surface catalogue **interne** au-dessus du Composer : Smart Library via `useResourceLibrary` + `resourceToSearchResult`. Portal → `#elfis-overlay-root` / body.

## Comportement

| Action | Résultat |
|--------|----------|
| Parcourir le catalogue | Ouvre sous-modale centrée (pas de route, pas de drawer) |
| Ajouter | Ligne → `draft.products`, toast « Ajouté », modal **reste ouverte** |
| Escape / Fermer / overlay | Ferme la sous-modale uniquement ; Composer reste ; focus → trigger |
| Nouveau produit | `ProductCreationDialog` au-dessus (z 1040) ; après création → reste dans catalogue + reload |

## Stack overlays (tokens `FP_OVERLAY_Z`)

Documents (0) < Composer backdrop (1000) < Composer (1010) < submodal backdrop (1020) < CatalogModal (1030) < ProductCreation (1040)

## Cause F1.3.2.1

Le drawer CSS (`z-index: 70`) peignait **sous** le Composer (`80`) — voir audit `47-catalog-overlay-layering-audit.md`.
