# Platform Shell V1 — Livrable

## Composants (`src/platform-shell/`)

| Composant | Rôle |
|-----------|------|
| `PlatformShell` | Frame chrome + sidebar slot + viewport |
| `PlatformTopBar` | Mark, launcher, search, org, workspace, notifs, profil |
| `PlatformLauncher` | Wrap `AppLauncher` (couleurs registry) |
| `PlatformSearch` | Palette UI mock (⌘K) |
| `NotificationCenter` | Panneau mock + filtres + lu |
| `OrganizationSwitcher` | Orgs auth réelles |
| `WorkspaceSwitcher` | UI workspaces locaux |
| `UserMenu` | Profil / org / prefs / logout |
| `ProductIndicator` | Mark + nom Pilot + by ELFIS |
| `PlatformSidebar` | Slot nav métier |
| `WorkspaceViewport` | Contenu Pilot |

## Démo

Route auth : **`/platform/shell`**

## Qualité

- Tests : `platform-shell.test.tsx`
- Pas de métier CRM/compta
- Pas de nouveau backend search/notifs
- Layouts Compta/Sales **non migrés** encore (dette P1.6+)

## Captures

Ouvrir `/platform/shell` connecté — desktop + resizer mobile (devtools).
