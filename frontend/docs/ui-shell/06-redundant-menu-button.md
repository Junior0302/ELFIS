# 06 — Suppression du 2ᵉ bouton menu topbar (UI.P2)

## Audit

| Bouton | Composant | Handler | Desktop | Mobile ≤900px | aria-label |
|--------|-----------|---------|---------|---------------|------------|
| **1 — hamburger ELFIS** | `PlatformTopBar` → `.ps-topbar__menu` | `PlatformShell.onGlobalMenuClick` → `GlobalNavigationDrawer` | visible | visible | dynamique Ouvrir/Fermer menu ELFIS |
| **2 — ex-toggle produit** | `PlatformTopBar` → `.ps-topbar__product-nav` (**retiré**) | ouvrait `mobileProductNavOpen` | était visible par bug CSS (`.ps-icon-btn` écrasait `display:none`) | visible | Ouvrir/Fermer navigation produit |

Cause visuelle : le 2ᵉ bouton restait dans le DOM ; `display: none` sur `.ps-topbar__product-nav` était annulé par `.ps-icon-btn { display: inline-grid }` déclaré après.

## Cible

Desktop : `[ Hamburger ELFIS ] [ Applications ] [ ELFIS Core ] [ ComptaPilot ]` — un seul hamburger.

Sidebar produit :

- Desktop : collapse interne UI.P1 (`.sidebar-collapse-btn` dans `ComptaProductNav`)
- Mobile/tablette : bouton **distinct** `.ps-shell__open-product-nav` dans le **contenu** (`WorkspaceViewport`), libellé « Navigation », glyphe ▤ — pas un 2ᵉ hamburger topbar. Fermeture via scrim.

## Changements

- Retrait React + props `showProductNavToggle` / `productNavOpen` / `onProductNavClick` de `PlatformTopBar`
- Styles orphelins `.ps-topbar__product-nav` / `.ps-product-nav-glyph` supprimés
- `aria-label` hamburger dynamique
- API sidebar : `openMobileNav` ajouté à côté de `closeMobileNav`

## Tests

`redundant-menu-button.test.tsx` — MB01–MB20.

```bash
npx vitest run src/platform-shell/redundant-menu-button.test.tsx
```
