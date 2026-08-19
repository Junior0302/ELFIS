# 01 — Runtime architecture audit (UX.UNIFY Vague 1–2)

**Date :** 2026-08-03  
**Scope :** Home (`/home`), Compta FCC (`/dashboard`), Sales Dashboard (`/sales`) + chrome shell.  
**Base :** code réel `frontend/src/` (pas de spéculation).

## Entrées auditées

| Environnement | Route | Layout | Shell runtime |
|---------------|-------|--------|---------------|
| ELFIS Core Home | `/home` | `ElfisHomeLayout` | `PilotWorkspace` → `ElfisUnifiedShell` → `PlatformShell` |
| ComptaPilot FCC | `/dashboard` | `WorkspaceLayout` | idem + accent Compta |
| SalesPilot Dashboard | `/sales` | `SalesWorkspaceLayout` | idem + accent Sales + collapse UI.P1 |

## Matrice Élément × Core / Compta / Sales × Cible × Composant × Migration × Risque × Statut

| Élément | Core | Compta | Sales | Cible | Composant | Migration | Risque | Statut |
|---------|------|--------|-------|-------|-----------|-----------|--------|--------|
| Frame shell | PilotWorkspace | PilotWorkspace | PilotWorkspace | 1 chrome | `ElfisUnifiedShell` | Alias PlatformShell | Faible | **GO** |
| Topbar navy | Oui | Oui | Oui | Identique | `GlobalTopbar` / `PlatformTopBar` | Préservé | Faible | **GO** |
| Hamburger UI.P2 | 1 | 1 | 1 | Un seul | Topbar menu | Préservé | Moyen | **GO** |
| Sidebar collapse UI.P1 | N/A mobile | 240/56 | 240/56 | Dims tokens | `PLATFORM_SHELL_DIMENSIONS` | Sales sync | Moyen | **GO** |
| Pastille Pilot | Masquée | Oui | Oui | Chrome config | `ProductIndicator` | Config | Faible | **GO** |
| Accents | Navy/bleu | Vert | Bleu | Accent only | `PilotTheme` / `PilotThemeProvider` | Tokens `--pilot-*` | Faible | **GO** |
| Nav config | Home custom JSX | `navModel` + ComptaProductNav | `salesNavModel` | Config sections | `NavigationSystem` + DomainNav | Contrat prêt ; adapters existants | Moyen | **Partiel** |
| Icônes | Glyphs Unicode | SVG `NavIcons` | Texte / initiale | Registre unique | `ElfisIconSystem` | Mapping central | Faible | **GO** |
| Page container | Custom → **migré** | Ad hoc → **migré** | Container lg → **xl** | `PlatformPageContainer` | unified-platform | 3 écrans | Faible | **GO** |
| Grille 12 | Custom CSS → **PlatformGrid** | WidgetGrid / CSS → **PlatformGrid** KPI/charts | Grid 4 → **PlatformGrid 12** | 12/8/4 | `PlatformGrid` / `GridItem` | 3 écrans | Faible | **GO** |
| Page header | HomeHero (métier) | Header FCC → **ElfisPageHeader** | PageHeader DS → **template** | Contrat 06 | `ElfisPageHeader` | 3 écrans | Faible | **GO** |
| Dashboard template | Structure Home | FCC sections | Sales sections | Template unifié | `ElfisDashboardTemplate` | Sales + structure FCC/Home | Faible | **GO** |
| Metric / KPI | Home cards métier | WidgetMetric → **ElfisMetricCard** | MetricCard → **ElfisMetricCard** | Surfaces neutres | wrappers DS | FCC + Sales | Moyen | **GO** |
| Charts | — | Widget chart → **ChartCard** | — | Surface neutre | `ChartCard` | FCC analyser | Moyen | **GO** |
| Buttons | Liens Home | `.btn` → **ElfisButton(Link)** | Mix Link/Button → **unifié** | DS Button | wrappers | 3 écrans | Faible | **GO** |
| Tables | — | Métier pages | — | Wrapper | `ElfisTable` | Prêt, pas migré pages | Faible | Prêt |
| Dialogs / forms | — | DS overlays | QuickCreateDrawer | Wrappers | `ElfisDialog*` / Form | Prêt | Faible | Prêt |
| Motion | CSS home | fcc-page-in | — | Tokens motion | `MotionSystem` / `MotionPage` | 3 écrans | Faible | **GO** |
| Feature flag | — | — | — | Opt-out | `UNIFIED_PLATFORM_UI` | Défaut on | Faible | **GO** |
| APIs / KPI data | lastProduct local | `financialApi.overview` | `getSalesDashboard` | **Inchangé** | — | Interdit de toucher | Élevé si touché | **Préservé** |
| Routes / permissions | `/home` | `/dashboard` + entitlements | `/sales` | **Inchangé** | App routes | Interdit | Élevé | **Préservé** |

## Écarts corrigés Vague 1–2

1. Contenu page sans container/grille plateforme → branché sur 3 écrans.
2. Sales Container `lg` (étroit) → `PlatformPageContainer` `xl`.
3. Boutons Sales hétérogènes (`Link.ds-btn` vs `Button`) → `ElfisButton` / `ElfisButtonLink`.
4. FCC verts massifs → surfaces `--up-surface-*` + accent Pilot (`up-fcc--unified`).
5. KPI FCC widgets → `ElfisMetricCard` ; charts → `ChartCard`.
6. Contrats Vague 2 (header / cards / template) → composants livrés.

## Écarts reportés (hors scope STOP)

- Migration pages secondaires (paramètres, listes, pipeline détail…).
- Remplacement runtime `ComptaProductNav` / `SalesProductNav` / `HomePlatformSidebar` par DomainNav seul (contrat prêt).
- Tables métier massives / rewrite widget-framework.

## Sources code

- `frontend/src/unified-platform/**`
- `frontend/src/platform-shell/**`
- `frontend/src/home/ElfisHomePage.tsx`
- `frontend/src/comptapilot/financial-command-center/FinancialCommandCenter.tsx`
- `frontend/src/pages/sales/SalesDashboardPage.tsx`
- Croisement : `frontend/docs/unified-experience/`
