# Navigation ELFIS — NAV.CORE.1

Architecture du menu principal plateforme : une config unique, deux modes d’affichage (sidebar + drawer).

## Statut

| Phase | Scope | Statut |
|-------|--------|--------|
| **NAV.CORE.1** | Sections, config unique, terminologie ELFIS, icons, footer, collapse | **Livré** |
| **NAV.DOMAIN.1** | Menus domaines métier Finance / Commercial | **Livré — voir [domain-boundaries](../domain-boundaries/)** |
| **BRAND.ELFIS.1** | Hub Espaces launcher | **Livré — voir [elfis-spaces](../elfis-spaces/) — STOP revue** |

## Index

| Doc | Contenu |
|-----|---------|
| [01](./01-current-navigation-audit.md) | Audit navigation AVANT |
| [02](./02-target-information-architecture.md) | IA cible + backlog |
| [03](./03-navigation-config-contract.md) | Contrat `elfisNavigationConfig` |
| [04](./04-icon-mapping.md) | Pictogrammes ElfisIconSystem |
| [05](./05-responsive-behavior.md) | Sidebar / drawer / collapse |
| [06](./06-test-plan.md) | NC01–NC30 |
| [07](./07-implementation-report.md) | Rapport GO |
| [08](./08-sidebar-proportion-parity.md) | Parité proportions Home = Finance / Commercial |

## Module

`frontend/src/platform-shell/global-nav/`

- `elfisNavigationConfig.ts` — source de vérité
- `ElfisGlobalNavigation.tsx` — rendu sidebar \| drawer
- `GlobalNavigationDrawer.tsx` — wrapper hamburger

Terminologie UI : **ELFIS** (pas « ELFIS Core » dans nav / footer visibles).

