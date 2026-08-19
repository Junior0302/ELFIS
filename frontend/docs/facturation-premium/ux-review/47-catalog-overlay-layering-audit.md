# 47 — Catalog overlay layering audit (F1.3.2.2)

## Symptômes observés

| # | Symptôme |
|---|----------|
| 1 | Catalogue **derrière** le Composer |
| 2 | Surface **floutée** avec l’arrière-plan Documents |
| 3 | Drawer latéral **partiellement hors écran** à droite |
| 4 | Focus / Escape incorrects (hiérarchie visuelle ≠ logique) |

## Surfaces auditées

- `DocumentCreationModalRoot` / `ComposerDialog` → `Portal` → `#elfis-overlay-root`
- `LibraryCatalogDrawer` → `Drawer` (`type: 'drawer'`, `modal`) → `Portal`
- `useOverlayBehaviour` + `OverlayManager` (`sortStack`, `parentOverlayId`)
- CSS `overlays.css` : `.ds-overlay-backdrop` / `--drawer` / `.ds-drawer`
- Stacking : `transform` sur preview PDF (`scale`), `overflow: hidden` Composer, `backdrop-filter` backdrops

## Cause exacte (pas un « bump z-index » aveugle)

1. **CSS fixe une inversion de pile**  
   - Dialog / Composer : `.ds-overlay-backdrop` → `z-index: var(--z-dialog, 80)`  
   - Drawer catalogue : `.ds-overlay-backdrop--drawer` → `z-index: var(--z-drawer, 70)`  
   - Panneau `.ds-drawer` → encore `z-index: 70`  
   → Le catalogue peignait **toujours sous** le Composer, même en enfant logique.

2. **OverlayManager calcule une pile mais ne l’applique pas au DOM**  
   `computeOverlayZIndex` / `sortStack` / `parentOverlayId` servent Escape / `isTopOverlay` / focus trap, **sans** `style.zIndex` sur le backdrop. La spécificité CSS gagne.

3. **Pattern drawer latéral inadapté**  
   `side="right"` + `position: fixed` + largeur ~28–36rem sur un Composer quasi plein écran → surface **coupée / hors viewport** à droite.

4. **Backdrop-filter**  
   Le backdrop Composer (`blur(2px)` + rgba sombre) reste au-dessus du drawer (z 80 > 70) → le catalogue, s’il est visible en transparence ou en bord, paraît **flouté / assombri** avec Documents.

5. **Focus**  
   Le drawer peut être top logique (`parentOverlayId` → trap Composer suspendu) alors qu’il est **invisible / derrière** → focus « perdu » / Escape ferme une surface non perçue.

## Correction retenue

- Remplacer le drawer par **`LibraryCatalogModal`** (sous-modale centrée, `type: dialog`)
- Tokens partagés `FP_OVERLAY_Z` (Documents → Composer → submodal → catalog → create)
- Portal body / overlay-root **hors** stacking context Composer
- Backdrop secondaire léger **sans** blur sur le panneau catalogue
- Focus trap unique sur la surface haute + restore « Parcourir le catalogue »

## Hors scope

Smart Library data, calculs métier, PDF engine, Vault, Billing, F1.4, fermeture Composer.
