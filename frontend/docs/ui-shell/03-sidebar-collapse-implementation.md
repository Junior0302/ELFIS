# 03 — Implémentation UI.P1 (collapse sync)

## Fichiers touchés

| Fichier | Changement |
|---------|------------|
| `platform-shell/productSidebarCollapse.ts` | Clés storage, lecture/écriture, notify resize, constantes |
| `platform-shell/useProductSidebarCollapsed.ts` | Hook état + persistance + notify post-transition |
| `platform-shell/platform-shell.css` | Vars, grid sync, collapsed rail, motion, mobile |
| `platform-shell/PlatformTopBar.tsx` | `WorkspaceViewport` + ResizeObserver |
| `platform-shell/ComptaProductNav.tsx` | Props contrôlées, a11y, tooltips, id nav |
| `platform-shell/ProductNavigation.tsx` | `id` optionnel sur `ProductSidebar` |
| `components/layouts/WorkspaceLayout.tsx` | Classe shell + wiring collapsed |
| `platform-shell/index.ts` | Exports publics utiles |
| Tests + docs `ui-shell/` | SC / SM / GO |

## Comportement collapsed (rail)

- Largeur grid = 56px.
- Libellés / chevrons / sous-menus : `display: none` (pas `visibility: hidden` avec largeur active).
- Icônes centrées ; toolbar collapse centrée.
- `title` + `aria-label` sur items quand collapsed (tooltip / clavier).
- Bouton : `aria-expanded`, `aria-controls`, label dynamique.

## Charts / viewport

- `WorkspaceViewport` observe sa taille (`ResizeObserver`) → `elfis:product-shell-viewport-resize`.
- Toggle collapse : after 180ms → même event + `window` `resize` (libs legacy).
- Graphs SVG existants (`width: 100%`) se reflowent sans F5 dès que la grille se resserre.

## Non-régression

- Topbar reste full-bleed au-dessus du body.
- Composer / routes / moteurs non modifiés.
- SalesPilot : pas de classe collapsed → rail expanded inchangé.
