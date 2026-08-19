# 26 — DocumentCreationModalRoot (F1.3.1.3)

Root unique (`ComposerDialog.tsx` → `DocumentCreationModalRoot`) :

- Un portail
- Focus trap Overlay Manager
- Scroll lock
- `aria-modal`
- Escape / backdrop selon stage
- Inert Documents (`[data-billing-layout="fp05"]`)
- Transition taille 150–240 ms (`prefers-reduced-motion: reduce`)
- **`closeOnRouteChange: false`** (anti-régression OverlayRouteBridge)
- Ignore `reason === 'route_change'` dans `handleClose`

Alias `ComposerDialog({ phase })` conservé pour tests F1.3.1.2.
