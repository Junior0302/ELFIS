# Platform Shell Integration P1.6 — Livrable

## Migration

| Layout | Statut |
|--------|--------|
| `WorkspaceLayout` | → `PlatformShell` + `ComptaProductNav` |
| `SalesWorkspaceLayout` | → `PlatformShell` + `SalesProductNav` |

Topbar unique : `PlatformTopBar` (Launcher, ProductIndicator, Search UI, Org, NotificationBell réel, UserMenu).

## Contrat

`productShellConfig.ts` → `ProductShellConfiguration` (pas de if produit dans le Shell).

## Notifications / Search

- Notifs : **NotificationBell** (service existant) dans la topbar.
- Search : UI only, **aucun résultat fictif**.
- `NotificationCenter` mock : conservé temporairement, plus utilisé dans la topbar.

## Supprimé / conservé

| | |
|--|--|
| **Supprimé des layouts** | topbars dupliquées, logout brut Sales, selects org dupliqués, brand « ComptaPilot IA » en sidebar |
| **Conservé** | `navModel`, trial, SubscriptionBanner, PageGuide, AppLauncher, NotificationBell, salesNavModel |
| **Plus tard** | retirer `NotificationCenter` mock ; brancher Search Engine ; migrer styles `.sidebar` legacy |

## Démo

`/platform/shell` inchangée.

## Dettes

- Styles nav Compta encore legacy (`.nav-categories`).
- WorkspaceSwitcher off par défaut.
- Validation manuelle login ↔ launcher à faire en runtime.
