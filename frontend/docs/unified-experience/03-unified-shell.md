# 03 — ElfisUnifiedShell

## Décision

**Consolider** `PlatformShell` plutôt que réécrire.  
`ElfisUnifiedShell` = façade Vague 1 (`pilotId`, classes `up-shell`) qui délègue 100 % au chrome UI.P1/P2.

## Composition

```
ElfisUnifiedShell / PilotWorkspace
└── PlatformShell
    ├── GlobalTopbar (= PlatformTopBar)
    ├── body
    │   ├── PilotSidebar (= PlatformSidebar) + nav métier
    │   └── PilotContentLayout (= WorkspaceViewport)
    └── GlobalNavigationDrawer
```

## Wrappers métier

Fournissent seulement : `pilotId`, `nav`, `title`, `chrome` overrides, `sidebarCollapsed`.  
Accents via `PilotTheme` (`applyPilotAccent`).

| Layout | Wrapper |
|--------|---------|
| Home | `PilotWorkspace` + `HomePlatformSidebar` |
| Compta | `PilotWorkspace` + `ComptaProductNav` |
| Sales | `PilotWorkspace` + `SalesProductNav` |
| Platform | `PilotWorkspace` `applyPilotAccent={false}` |
