# 08 — Critères GO / NO-GO (UI.P2)

## Checklist GO (9 points)

| # | Critère | Statut |
|---|---------|--------|
| 1 | Un seul bouton hamburger en haut à gauche | **GO** |
| 2 | Le bouton restant ouvre le menu global ELFIS | **GO** |
| 3 | Le 2ᵉ bouton n’existe plus dans le DOM (`.ps-topbar__product-nav`) | **GO** |
| 4 | Aucun espace vide résiduel dans la topbar left | **GO** |
| 5 | Sidebar produit fonctionne (desktop + overlay mobile) | **GO** |
| 6 | Responsive correct (contrôle mobile distinct, pas 2 hamburgers) | **GO** |
| 7 | Tests MB verts | **GO** (preuve : vitest) |
| 8 | TypeScript vert | **GO** (preuve : `npm run build`) |
| 9 | Build vert | **GO** (preuve : `npm run build`) |

**Résultat :** 9/9 GO — phase UI.P2 **STOP**.

## STOP

Ne pas enchaîner une autre phase UI shell / redesign global.

## NO-GO si

- Deux hamburgers encore côte à côte
- Masquage CSS seul (`visibility` / `opacity` / `display` sur un bouton toujours rendu en topbar)
- Nav produit mobile inaccessible
- Régression menu global / collapse UI.P1 / Composer
