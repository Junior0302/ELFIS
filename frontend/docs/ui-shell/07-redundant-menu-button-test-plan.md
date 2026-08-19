# 07 — Plan de tests bouton menu redondant (UI.P2)

## Automatisés (MB01–MB20)

Fichier : `frontend/src/platform-shell/redundant-menu-button.test.tsx`

| ID | Cas |
|----|-----|
| MB01 | Un seul hamburger dans la topbar |
| MB02 | Bouton global ouvre le drawer |
| MB03 | `.ps-topbar__product-nav` absent du DOM + CSS |
| MB04 | Pas d’espace vide : Apps suit le hamburger |
| MB05 | Pas de focus fantôme sur l’ancien toggle |
| MB06 | Menu global ouvre + aria Fermer |
| MB07 | Menu global ferme (Escape) |
| MB08 | Sidebar produit présente |
| MB09 | Collapse interne UI.P1 OK |
| MB10 | Shell ComptaPilot |
| MB11 | Shell Finance sans 2ᵉ hamburger |
| MB12 | Shell Facturation sans 2ᵉ hamburger |
| MB13 | Composer focus masque contrôle nav contenu |
| MB14 | CSS tablette : open-product-nav, pas product-nav topbar |
| MB15 | Mobile : ouverture via bouton distinct contenu |
| MB16 | Clavier Entrée → menu ELFIS |
| MB17 | aria-label dynamique Ouvrir/Fermer |
| MB18 | Props produit retirées de PlatformTopBar |
| MB19 | Pas de styles orphelins topbar product-nav |
| MB20 | SalesPilot + persistence collapse sans régression |

```bash
npx vitest run src/platform-shell/redundant-menu-button.test.tsx
```

## Manuels — À tester manuellement

| ID | Scénario |
|----|----------|
| MM01 | Desktop : un seul hamburger à gauche |
| MM02 | Clic hamburger → menu global |
| MM03 | Pas de 2ᵉ icône menu à côté |
| MM04 | Collapse sidebar Compta (chevron interne) |
| MM05 | ≤900px : bouton « Navigation » dans le contenu |
| MM06 | ≤900px : Navigation ouvre overlay sidebar |
| MM07 | Scrim ferme la nav produit |
| MM08 | SalesPilot / Home : même topbar mono-hamburger |
| MM09 | Composer modal : pas de conflit chrome |
| MM10 | Lecteur d’écran : labels Ouvrir/Fermer menu ELFIS |
