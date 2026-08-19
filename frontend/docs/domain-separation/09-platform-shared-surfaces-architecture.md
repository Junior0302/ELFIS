# 09 — Platform shared surfaces architecture

```
PlatformShell (chrome global)
└── PlatformWorkspaceLayout   ← S1.1
    ├── PlatformNavigation    (ELFIS Core)
    └── Outlet

≠ WorkspaceLayout (ComptaProductNav)
≠ SalesWorkspaceLayout (SalesProductNav)
≠ ElfisHomeLayout (sidebar Home — /home uniquement)
```

## Routes workspace

| Route | Surface |
|-------|---------|
| `/platform/organization` | Identité org |
| `/platform/members` | Membres / invitations / rôles |
| `/platform/teams` | → members (pas d’écran séparé) |
| `/platform/roles` | → members |
| `/platform/documents` | Vault global |
| `/platform/communications` | État e-mail |
| `/platform/communications/settings` | Infra e-mail |
| `/platform/aura` | Assistant global |
| `/platform/relations` | Lecture unifiée |
| `/platform/settings` | Hub paramètres |

## Design

- Topbar navy PlatformShell
- Sidebar sombre plateforme (`ps-sidebar--platform`)
- Viewport clair
- Pas de dominante verte Compta / bleue Sales
- ProductIndicator masqué sur Core

## Permissions (mapping temporaire)

| Capacité cible | Permission existante |
|----------------|----------------------|
| platform.organization.* | org `can_edit` / membership |
| platform.members.* | `users.manage` |
| platform.documents.* | `documents.read` |
| platform.aura.use | `ai.analysis` |
| platform.communications.* | membership + flags `can_manage` email |
| platform.relations.* | `invoice.read` implicite via list APIs |

Dette : formaliser permissions `platform.*` en S1.2.
