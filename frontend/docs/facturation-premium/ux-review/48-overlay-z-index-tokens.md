# 48 — Overlay z-index tokens (F1.3.2.2)

## Tokens TS

`frontend/src/comptapilot/facturation/overlayLayers.ts` → `FP_OVERLAY_Z`

| Clé | Valeur | Usage |
|-----|--------|-------|
| documents | 0 | page Documents |
| composerBackdrop | 1000 | backdrop Composer |
| composerDialog | 1010 | panneau Composer |
| submodalBackdrop | 1020 | backdrop catalogue |
| catalogModal | 1030 | panneau catalogue |
| nestedCreate | 1040 | Nouveau produit |

## CSS

`:root` dans `facturation-spaces.css` + `library-catalog-modal.css` (`--fp-z-*`).

## Règle

Pas de z-index magiques dispersés. Inline `style={{ zIndex: FP_OVERLAY_Z.* }}` pour gagner sur `.ds-overlay-backdrop` (80/70).
