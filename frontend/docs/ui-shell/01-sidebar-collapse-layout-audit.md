# 01 — Audit collapse sidebar ComptaPilot (UI.P1)

**Date :** 2026-08-03  
**Scope :** shell ComptaPilot uniquement (`WorkspaceLayout` → `PlatformShell` → `ComptaProductNav`).  
**Hors scope :** Composer, routes, données métier, moteurs, SalesPilot collapse.

## Symptôme

Sidebar « réduite » : libellés disparus, icônes visibles, **mais** le contenu principal conserve la colonne / marge de la sidebar ouverte → bande vide à gauche.

## Chaîne de composants

| Couche | Fichier | Rôle |
|--------|---------|------|
| Layout produit | `components/layouts/WorkspaceLayout.tsx` | Monte `PlatformShell` + slot `ComptaProductNav` |
| Shell | `platform-shell/PlatformShell.tsx` | Topbar pleine largeur + `ps-shell__body` (grid sidebar / viewport) |
| Sidebar DOM | `PlatformTopBar.tsx` → `PlatformSidebar` | `<aside class="ps-sidebar">` |
| Nav métier | `ComptaProductNav.tsx` | État `collapsed` local + classe `is-collapsed` |
| CSS shell | `platform-shell/platform-shell.css` | `--ps-sidebar-w: 240px` + grid |
| CSS legacy | `index.css` `.app-shell` / `.sidebar.is-collapsed` | Ancien pattern sync grid (278↔84) **non branché** sur PlatformShell |

## État collapsed (avant fix)

- **Source :** `useState` dans `ComptaProductNav` uniquement.
- **Persistance :** `localStorage` clé `cp_sidebar_collapsed` (`'1'` / `'0'`).
- **Effet UI :** classe `compta-product-nav.is-collapsed` → `display: none` sur `.nav-text`, chevrons, sous-menus, lien admin.
- **Non propagé :** aucune classe / attribut / variable CSS sur `.ps-shell` ni sur `.ps-shell__body`.

## Largeurs / layout (avant fix)

| Token / règle | Valeur | Consommateur |
|---------------|--------|--------------|
| `--ps-sidebar-w` | **240px fixe** | `.ps-shell--with-sidebar .ps-shell__body { grid-template-columns: var(--ps-sidebar-w) 1fr }` |
| `--product-sidebar-*` | **absent** | — |
| `margin-left` / `padding-left` contenu | non hardcodé 168px sur viewport | Viewport = 2ᵉ colonne grid |
| Topbar | pleine largeur flex (hors grid body) | OK — pas de `left: 168px` |
| Mobile `≤900px` | `grid-template-columns: 1fr` + sidebar `position: fixed` overlay | OK hors desktop |

## Cause exacte

**Découplage état nav ↔ largeur shell.**

1. Le collapse ComptaPilot ne réduit **que** le contenu interne de la nav (masquage des libellés).
2. La grille du shell réserve **toujours** `240px` via `--ps-sidebar-w` inchangé.
3. Résultat : la 1ʳᵉ colonne grid reste à 240px (icônes centrées dans un rail trop large / vide ressenti côté contenu), le viewport ne s’élargit pas.

Le legacy `.app-shell.sidebar-collapsed { grid-template-columns: 84px 1fr }` montrait le pattern correct, mais **n’est plus utilisé** depuis la migration `PlatformShell` (P1.6) : `ComptaProductNav` a repris le toggle sans reconnecter la grille.

## Sticky / topbar

- `.ps-topbar` : flex child du shell, **pleine largeur** — pas de offset sidebar.
- Pas de header sticky métier avec `left` / `width: calc(100% - 168px)` identifié sur le chrome shell.
- Risque futur : tout sticky page avec largeur hardcodée doit consommer `--product-sidebar-current-width`.

## Charts

- FCC / dashboard : SVG `width: 100%` + `viewBox` — se reflowent si le conteneur change de largeur.
- Sans réduction de la colonne grid, le conteneur ne change pas → pas de « resize » visible (bande vide).
- Besoin : sync largeur shell **puis** signal ResizeObserver / événement viewport pour libs canvas éventuelles.

## Synthèse

| Attendu collapse | Comportement observé (avant) | Après UI.P1 |
|------------------|------------------------------|-------------|
| Rail ~52–64px | Rail grid 240px | `--product-sidebar-current-width` → 56px |
| Viewport élargi immédiatement | Viewport inchangé | Grid sync via classe shell |
| Une seule variable largeur | `--ps-sidebar-w` fixe + collapse nav isolé | expanded / collapsed / current |

**Correction :** `WorkspaceLayout` possède l’état collapsed → `PlatformShell.sidebarCollapsed` + `ComptaProductNav` contrôlée ; CSS `grid-template-columns: var(--product-sidebar-current-width) minmax(0, 1fr)`.
