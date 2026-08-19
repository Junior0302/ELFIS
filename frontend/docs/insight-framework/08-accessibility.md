# 08 — Accessibility

## ARIA & rôles

- `critical` / type critique → `role="alert"`
- Autres → `role="status"` (toast : `aria-live="polite"`)
- Listes : `aria-label="Insights"`
- Actions : `role="group"` + `aria-label="Actions"`
- Pourquoi ? : `aria-expanded`, `aria-controls`

## Clavier & focus

- Boutons / liens focusables
- `focus-visible` outline contrasté (accent)
- Pas de piège focus

## Contraste

- Texte sur fond `color-mix` léger de l’accent DS
- Badges uppercase lisibles ; icônes `aria-hidden` sauf titre fourni

## Screen readers

- Titre + summary toujours dans le flux
- Source / confiance / timestamp en footer (si présents)
- Dismiss : `aria-label="Ignorer"`
