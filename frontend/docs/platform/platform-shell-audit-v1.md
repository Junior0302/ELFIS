# Platform Shell — Audit V1

**Phase :** chrome plateforme  
**Date :** 2026-08-01  
**Portée :** lecture seule des shells existants → base du module `src/platform-shell/`.

---

## Inventaire

| Surface | Fichier | Rôle |
|---------|---------|------|
| Shell Compta | `components/layouts/WorkspaceLayout.tsx` | Topbar + sidebar métier + notifs + search + org + outlet |
| Shell Sales | `components/layouts/SalesWorkspaceLayout.tsx` | Topbar + sidebar Sales + launcher + org ; **pas** search/notifs |
| Launcher | `app-launcher/*` | Popover/Drawer, ProductMark, sections état produit |
| Theme | `RuntimeThemeSync` + `ProductThemeProvider` | Produit = route |
| Notifs | `NotificationBell.tsx` | API réelle, Compta only |
| Search | `GlobalSearchBar.tsx` | Lien `/search`, Compta only |
| Admin cockpit | `components/platform/*` | **Autre** shell (elfadmin) — ne pas confondre |

---

## Réutilisable

- `AppLauncher` + `ProductMark` + `buildLauncherSections`
- Overlays DS : `Popover`, `Drawer`
- `Button`, `Input`, `Badge`, `cx`
- `layoutUtils` (`userInitials`)
- Tokens `--pilot-*`

---

## Duplication / héritage

| Problème | Détail |
|----------|--------|
| Deux shells produit | Compta legacy CSS vs Sales `--pilot-*` |
| Org switcher ×3 | `<select>` natifs divergents |
| Profil | Chip `/compte` vs dropdown logout-only |
| Branding | favicon « ComptaPilot IA » vs ProductMark |
| Search / Notifs | Absents de Sales |
| Nom collision | `PlatformLayout` admin ≠ Platform Shell multi-Pilot |

---

## Points bloquants (migration layouts)

1. Nav métier couplée (`navModel` / trial) dans WorkspaceLayout  
2. CSS global `.app-shell` vs tokens  
3. SyncProvider requis pour notifs API actuelles  
4. Paths thème incomplets pour certaines routes  

**Décision :** nouveau module `src/platform-shell/` — chrome unifié.  
Les layouts métier migreront en consommant `<PlatformShell>` + slot sidebar / viewport (phase ultérieure).  
Cette phase livre le chrome + page de démonstration authentifiée.

---

## Interdictions respectées

Pas de CRM, facturation, dashboard métier, moteur search/notifs backend, SSO externes.
