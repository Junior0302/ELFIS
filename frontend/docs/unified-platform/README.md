# Unified Platform — ELFIS ONE

Programme **UX.UNIFY** : une seule interface ELFIS. Modules = domaines, pas apps isolées.

Croise [unified-experience](../unified-experience/) (Vague 1 partielle).

## Statut

| Vague | Scope | Statut |
|-------|--------|--------|
| **1** | Shell, topbar, sidebar, tokens, icons, nav config, PilotTheme | **Livré** |
| **2** | Header, cards, ChartCard, DashboardTemplate, wrappers DS, motion | **Livré** |
| **Pilote** | Home + FCC `/dashboard` + Sales Dashboard | **Livré** |
| **1.2 Spatial** | Frame 1680, sidebar navy, compositions 3 dashboards | **STOP captures** |
| 3+ | Pages secondaires | **Interdit** avant validation |

## Index 01–34

| Doc | Contenu |
|-----|---------|
| [01](./01-runtime-architecture-audit.md) | Audit matrice |
| [02](./02-vision.md) | Vision plateforme unique |
| [03](./03-unified-shell.md) | ElfisUnifiedShell |
| [04](./04-navigation-system.md) | NavigationSystem |
| [05](./05-sidebar.md) | Sidebar domaine |
| [06](./06-icon-system.md) | ElfisIconSystem |
| [07](./07-pilot-themes.md) | PilotTheme |
| [08](./08-tokens.md) | Tokens |
| [09](./09-typography.md) | Typo |
| [10](./10-grid.md) | Grid |
| [11](./11-page-header.md) | PageHeader |
| [12](./12-dashboard-template.md) | DashboardTemplate |
| [13](./13-cards.md) | Cards / KPI / Chart |
| [14](./14-buttons-forms.md) | Buttons / Forms |
| [15](./15-tables.md) | Tables |
| [16](./16-dialogs.md) | Dialogs |
| [17](./17-motion.md) | Motion |
| [18](./18-responsive.md) | Responsive |
| [19](./19-accessibility.md) | A11y |
| [20](./20-routing.md) | Routing |
| [21](./21-migration.md) | Migration |
| [22](./22-three-screen-pilot.md) | 3 écrans pilotes |
| [23](./23-test-plan.md) | Tests UXU / OP |
| [24](./24-implementation-report.md) | Rapport GO |
| [25](./25-page-frame-layout-control.md) | Page frame — contrôle largeur réel |
| [26](./26-spatial-runtime-audit.md) | Audit spatial AVANT |
| [27](./27-spatial-comparative.md) | Comparatif AVANT→APRÈS |
| [28](./28-sidebar-navy.md) | Sidebar navy unique |
| [29](./29-page-frame-1680.md) | Contrat frame 1680 |
| [30](./30-dashboard-sections.md) | Sections template |
| [31](./31-card-dimensions.md) | Metric / Chart dims |
| [32](./32-three-dashboard-compositions.md) | Compositions Home/FCC/Sales |
| [33](./33-test-plan-uss.md) | USS / USM |
| [34](./34-uss-implementation-report.md) | Rapport GO 1.2 + STOP |
| [35](./35-blind-template-identity.md) | Blind test — 1 template DS |

## Module

`frontend/src/unified-platform/`

## Non-objectifs

Pas rewrite APIs/moteurs ; pas 3 DS ; pas pages secondaires avant revue.
