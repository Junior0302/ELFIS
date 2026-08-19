# 05 — Comportement responsive

## Desktop

- Sidebar permanente (`ElfisGlobalNavigation` mode `sidebar`)
- Mêmes sections / items / footer que le drawer
- Collapse UI.P1 : `useProductSidebarCollapsed` + `sidebarCollapsed` sur `PilotWorkspace`
- Collapse : labels masqués, titres section masqués, tooltips (`title` / `aria-label`), icônes conservées, pas d’espace fantôme

## Tablette / mobile

- Drawer hamburger = même config (`mode="drawer"`)
- Ouverture sidebar produit mobile inchangée (scrim shell)
- Pas de navigation mobile ad hoc

## État actif

- Navy / bleu institutionnel (`--elfis-gnav-accent`, bord gauche)
- Identique sidebar, drawer, mobile (même `isElfisNavItemActive`)

