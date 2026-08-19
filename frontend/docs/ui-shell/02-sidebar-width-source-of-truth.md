# 02 — Source unique de largeur sidebar

## Variables CSS (contrat)

Définies sur `.ps-shell` :

| Variable | Rôle | Valeur cible |
|----------|------|--------------|
| `--product-sidebar-expanded-width` | Rail ouvert | `240px` |
| `--product-sidebar-collapsed-width` | Rail réduit | `56px` (dans 52–64) |
| `--product-sidebar-current-width` | Largeur active | expanded **ou** collapsed |
| `--ps-sidebar-w` | Alias rétrocompat | `var(--product-sidebar-current-width)` |

## Règle d’or

Sidebar **et** contenu (grid / margin / calc) consomment **uniquement** `--product-sidebar-current-width`.  
Interdit : `margin-left: 240px`, `168px`, ou seconde source de vérité JS pour la largeur layout.

## Layout cible

```css
.ps-shell--with-sidebar .ps-shell__body {
  grid-template-columns: var(--product-sidebar-current-width) minmax(0, 1fr);
  transition: grid-template-columns 180ms ease;
}
```

État collapsed = classe shell `ps-shell--sidebar-collapsed` (posée par `WorkspaceLayout` ComptaPilot) :

```css
.ps-shell--sidebar-collapsed {
  --product-sidebar-current-width: var(--product-sidebar-collapsed-width);
}
```

## Transition

- Durée **180ms** sur `grid-template-columns` (et overflow sidebar si besoin).
- `prefers-reduced-motion: reduce` → `transition: none`.
- Après transition : événement `elfis:product-shell-viewport-resize` (+ miroir `resize` fenêtre optionnel).

## Persistance

- Clé : `elfis.productSidebarCollapsed` (`1` / `0`).
- Migration lecture : legacy `cp_sidebar_collapsed`.
- Init synchrone dans `useState` → pas de flash expanded→collapsed.
- **Pas** de redirect route.

## Mobile / tablette (`≤900px`)

- Grid body = `1fr` (aucune largeur desktop réservée).
- Sidebar = drawer / overlay `position: fixed` ; fermée = hors écran, contenu 100 %.
- Classe collapsed desktop n’impose **pas** de marge sur viewport mobile.
