# Unified Experience — ELFIS Core / ComptaPilot / SalesPilot

Socle visuel unifié (phase **UX.UNIFY.1**). Même shell, topbar, sidebar, container, grille, tokens. **Accent Pilot seulement.**

Croise le programme complet : [unified-platform](../unified-platform/) (Vague 1–2 + 3 écrans pilotes).

## Statut

| Vague | Scope | Statut |
|-------|--------|--------|
| **1** | Tokens, shell, topbar, sidebar, container, grid, PilotTheme, 3 entrées | **Livré** — étendu dans `unified-platform/` |
| **2** | Header / cards / KPI / template dashboards | **Livré** (voir `unified-platform/`) |
| Pilote 3 écrans | Home + FCC + Sales | **STOP captures/revue** |
| 3+ | Pages secondaires | Interdit avant validation |

## Index docs

| Doc | Contenu |
|-----|---------|
| [01 — Audit runtime](./01-runtime-visual-audit.md) | Matrice Élément × 3 environnements × Cible × Migration |
| [02 — Tokens](./02-platform-tokens.md) | Spacing, radius, shadows, borders, surfaces, typography |
| [03 — Shell](./03-unified-shell.md) | ElfisUnifiedShell / PlatformShell |
| [04 — Topbar](./04-global-topbar.md) | Ordre, navy, pastille, hamburger UI.P2 |
| [05 — Sidebar](./05-pilot-sidebar.md) | Structure commune, collapse UI.P1 |
| [06 — Page header](./06-page-header-contract.md) | Contrat Vague 2 |
| [07 — Cards / KPI](./07-cards-kpi-contract.md) | Contrat Vague 2 |
| [08 — Dashboard template](./08-dashboard-template-contract.md) | Contrat Vague 2 |
| [09 — Container](./09-page-container.md) | PlatformPageContainer |
| [10 — Grid](./10-platform-grid.md) | PlatformGrid / GridItem 12/8/4 |
| [11 — PilotTheme](./11-pilot-theme.md) | Accents Core / Compta / Sales |
| [12 — Migration](./12-migration-plan.md) | Plan progressif + flag |
| [13 — Tests](./13-test-plan.md) | UXU01–60 |
| [14 — Rapport](./14-implementation-report.md) | GO / NO-GO Vague 1 |

## Module code

`frontend/src/unified-platform/`

- `ElfisUnifiedShell` / `PilotWorkspace` → délègue à `PlatformShell` (pas de 2e chrome)
- `GlobalTopbar` / `PilotSidebar` / `PilotContentLayout` → alias
- `PlatformPageContainer`, `PlatformGrid` / `GridItem`
- `PilotTheme`, `platformTokens`, flag `UNIFIED_PLATFORM_UI`

## Non-objectifs Vague 1

- Pas de rewrite frontend entier
- Pas 3 Design Systems
- Pas migration massive cards/KPI/tables
- Pas pages secondaires avant validation
- Aucune modif données / APIs / moteurs / workflows / routes métier
