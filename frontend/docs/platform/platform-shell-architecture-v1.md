# Platform Shell — Architecture V1

```
PlatformShell
├── PlatformTopBar
│   ├── ProductIndicator (Mark + nom Pilot)
│   ├── PlatformLauncher (wrap AppLauncher)
│   ├── PlatformSearch (UI only)
│   ├── OrganizationSwitcher
│   ├── WorkspaceSwitcher
│   ├── NotificationCenter (UI + mock)
│   └── UserMenu
├── PlatformSidebar? (slot optionnel)
└── WorkspaceViewport (children / Outlet)
```

## Contrat Pilot

```tsx
<PlatformShell
  productId="salespilot"
  sidebar={<ProductNav />}   // optionnel
>
  <WorkspaceViewport>
    {/* contenu métier */}
  </WorkspaceViewport>
</PlatformShell>
```

Ou simplement `children` dans le viewport.

## Identité

- Chrome neutre / navy  
- Accent = primary du Pilot courant (indicateur + focus)  
- Pas de dominante verte globale  
- Aligné Landing / Login / Brand Book  

## Fichiers

`frontend/src/platform-shell/*`

## Route démo

`/platform/shell` (auth) — viewport placeholder, chrome interactif.
