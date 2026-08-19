# 05 — Critères GO / NO-GO (UI.P1)

## Checklist GO (11 points)

| # | Critère | Statut |
|---|---------|--------|
| 1 | Audit documenté + cause exacte (nav collapse ≠ largeur grid) | **GO** |
| 2 | Variables `--product-sidebar-expanded/collapsed/current` | **GO** |
| 3 | Sidebar + contenu : **même** variable (grid) | **GO** |
| 4 | Collapse → viewport élargi immédiatement (plus de bande vide) | **GO** |
| 5 | Transition 180ms sync + `prefers-reduced-motion` | **GO** |
| 6 | Rail collapsed 52–64px, icônes centrées, pas d’espace texte fantôme | **GO** |
| 7 | Charts / viewport : ResizeObserver + event (sans F5) | **GO** |
| 8 | Topbar pleine largeur ; pas d’offset hardcodé 168px | **GO** |
| 9 | Persistance `elfis.productSidebarCollapsed`, pas de flash, pas de redirect | **GO** |
| 10 | Mobile/tablette : overlay, contenu 100 % si fermée | **GO** |
| 11 | a11y : aria-label dynamique, aria-expanded, aria-controls, titles | **GO** |

**Résultat :** 11/11 GO — phase UI.P1 **STOP**.

Preuve auto : `npx vitest run src/platform-shell/sidebar-collapse.test.tsx` → SC01–SC40 verts.

## STOP

Phase UI.P1 **terminée** lorsque les 11 points sont GO, tests SC verts, build OK.  
**Ne pas** enchaîner une phase visuelle globale, ni toucher Composer / routes / métier / moteurs.

## NO-GO si

- Grid reste à 240px en collapsed
- Double source de largeur (margin hardcodée ≠ var)
- Flash de layout au reload
- Régression mobile (marge desktop sur petit écran)
