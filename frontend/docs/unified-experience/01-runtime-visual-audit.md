# 01 — Audit runtime visuel (Vague 1)

**Date :** 2026-08-03  
**Scope :** Home (`/home`), Compta dashboard (`/dashboard`), Sales dashboard (`/sales`) + chrome shell.

## Entrées auditées

| Environnement | Layout | Shell avant | Shell après Vague 1 |
|---------------|--------|-------------|---------------------|
| ELFIS Core Home | `ElfisHomeLayout` | `PlatformShell` | `PilotWorkspace` → `ElfisUnifiedShell` → `PlatformShell` |
| ComptaPilot | `WorkspaceLayout` | `PlatformShell` + collapse | idem + accents PilotTheme |
| SalesPilot | `SalesWorkspaceLayout` | `PlatformShell` (pas collapse) | + collapse UI.P1 |
| Platform workspace | `PlatformWorkspaceLayout` | `PlatformShell` | `PilotWorkspace` (sans accent home forcé) |

## Matrice Élément × 3 × Cible × Migration

| Élément | Core Home | Compta | Sales | Cible unifiée | Migration Vague 1 |
|---------|-----------|--------|-------|---------------|-------------------|
| Frame shell | PlatformShell | PlatformShell | PlatformShell | ElfisUnifiedShell (= PlatformShell) | Alias + `up-shell` |
| Topbar navy | Oui (`--platform-shell-bg`) | Oui | Oui | Identique navy | Déjà OK |
| Hamburger ELFIS | 1 (UI.P2) | 1 | 1 | Un seul | Préservé |
| Pastille Pilot | Masquée (Home) | ProductIndicator | ProductIndicator | Pastille si Pilot ≠ Home | Config chrome |
| Sidebar width | 240 / mobile | 240 / 56 collapse | 240 fixe → **56 collapse** | 240 / 56 UI.P1 | Sales branché |
| Accent | Navy Core | Vert Compta | Bleu Sales | Accent only via PilotTheme | `resolvePilotTheme` |
| Tokens spacing | foundation :root | idem | idem | PLATFORM_* aliases | Doc + CSS `--up-*` |
| Page container | Ad hoc Home | Ad hoc pages | Ad hoc | PlatformPageContainer | Composant prêt |
| Grille 12-col | Non | Partial ds-grid | Partial | PlatformGrid 12/8/4 | Composant prêt |
| Cards / KPI | Home cards | Dashboard Compta | Dashboard Sales | Vague 2 | **Pas migré** |
| Tables | — | Métier | Métier | Vague 3 | **Pas migré** |

## Écarts corrigés Vague 1

1. **Sales sans collapse** → sync grille `--product-sidebar-*` + toolbar collapse.
2. **API publique fragmentée** → `unified-platform` + wrappers `PilotWorkspace`.
3. **Pas de grille 12 documentée** → `PlatformGrid` / `GridItem`.
4. **Tokens shell dispersés** (`--ps-*` vs foundation) → aliases `--up-*` sous `.up-shell--unified`.

## Écarts reportés (Vague 2+)

- Harmonisation cards/KPI/empty Home vs dashboards
- PageHeader contrat unique
- Template dashboard partagé
- Pages secondaires (paramètres, listes métier)

## Sources code

- `platform-shell/PlatformShell.tsx`, `PlatformTopBar.tsx`, `platform-shell.css`
- `design-system/tokens/foundationTokens.ts`, `tokens/pilotTokens.ts`
- `home/ElfisHomeLayout.tsx`, `components/layouts/WorkspaceLayout.tsx`, `SalesWorkspaceLayout.tsx`
- Docs UI.P1 / UI.P2 : `frontend/docs/ui-shell/`
