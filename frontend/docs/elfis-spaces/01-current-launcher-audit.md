# 01 — Audit launcher actuel (AVANT BRAND.ELFIS.1)

## Surface

| Élément | Avant | Problème |
|---------|-------|----------|
| Topbar trigger | **Applications** | Vocabulaire produit / apps |
| Dialog title | Applications ELFIS | Orienté multi-apps |
| Sous-titre | « expertises depuis un seul espace » | OK proche, pas « métiers » |
| Cartes | ComptaPilot, SalesPilot, DocPilot… | Identité moteur en premier plan |
| Carte active | Produit actif (ComptaPilot) | ELFIS parfois perçu comme app |
| Continuer | Continuer / Commencer avec **ComptaPilot** | Nom moteur |
| Search | « Rechercher une application » | Exige de connaître les Pilots |
| Footer | ELFIS Home, Découvrir… | Libellé Home + découverte modules |
| Coming soon | Cartes Pilots + chips | Cohérent mais pas domaines |

## Architecture technique (conservée)

```
PlatformLauncher → AppLauncher
  Dialog / Drawer + Overlay Manager
  productEntryRoutes (/dashboard, /sales)
  lastProduct (localStorage)
  Product Registry (signature moteurs)
```

## Décision

Remodeler **uniquement** UX / terminologie / structure cartes domaines.
Ne pas toucher aux moteurs, ni aux routes SPA existantes, ni à la Home.
