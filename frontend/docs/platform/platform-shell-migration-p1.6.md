# Platform Shell — Migration Audit P1.6

## Matrice

| Surface | Ancien | Nouveau | Données | Risque | Stratégie |
|---------|--------|---------|---------|--------|-----------|
| Frame Compta | `WorkspaceLayout` chrome | `PlatformShell` | productId comptapilot | Moyen (nav complexe) | Remplacer chrome, garder nav + trial |
| Frame Sales | `SalesWorkspaceLayout` chrome | `PlatformShell` | productId salespilot | Faible | Remplacer entièrement le chrome |
| Topbar | desktop-topbar / sales-topbar | `PlatformTopBar` | auth, thème route | Moyen | Une seule topbar |
| Launcher | `AppLauncher` ×2 layouts | `PlatformLauncher` → AppLauncher | registry | Faible | Une instance |
| Search | `GlobalSearchBar` | `PlatformSearch` UI | — | Faible | UI only, pas de faux résultats |
| Notifs | `NotificationBell` | `NotificationBell` dans topbar | Sync/API | Faible | Brancher réel, retirer mock |
| Org | `<select>` | `OrganizationSwitcher` | memberships | Moyen | close overlays + setOrgId |
| Profil / logout | chip + logout sidebar | `UserMenu` | auth | Faible | logout → /login |
| Sidebar Compta | `.sidebar` navModel | slot + `ComptaProductNav` | permissions, trial | Élevé | Extraire nav intacte |
| Sidebar Sales | sales-nav | `SalesProductNav` | SALES_NAV_ITEMS | Faible | ProductNavigationItem |
| Theme | RuntimeThemeSync | inchangé | path | Critique | Ne jamais setCurrentProduct dans layout |
| Guards | ProductAccessLayout | inchangé | phase | Faible | Garde choisit layout migré |
| Demo | `/platform/shell` | conservée | — | Nul | Inchangée |

## Interdit

Pas de `if product === salespilot` dans PlatformShell — configs via registry.
