# 49 — LibraryCatalogModal UX (F1.3.2.2)

## Dimensions desktop

- Width : `clamp(620px, 72vw, 820px)`
- Min-height : `min(72vh, 760px)`
- Max-height : `min(88vh, 900px)`
- Centré (`place-items: center`)

## Backdrop

`rgba(8, 19, 30, 0.28)` — **sans** `backdrop-filter` sur le catalogue (panneau net).

## Structure

Header · Search · Filtres Tous/Produits/Services/Packs · Liste · Footer (Nouveau produit + Fermer)

## Motion

180–220ms ; `prefers-reduced-motion: reduce` → aucune animation.
