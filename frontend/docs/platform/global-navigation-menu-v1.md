# Menu global ELFIS — Navigation V1 (S1.1.1)

## Cause du bouton inutilisable

| Élément | Fichier | État avant | Cause | Correction |
|---------|---------|------------|-------|------------|
| Hamburger | `PlatformTopBar.tsx` | Masqué desktop (`display: none`) | CSS mobile-only | Toujours visible |
| Callback | `PlatformShell.tsx` | Toggle sidebar produit | Confondu avec nav globale | Ouvre `GlobalNavigationDrawer` |
| Sans sidebar | `PlatformShell` | `onMenuClick` undefined | Pas de bouton | Toujours branché |
| Overlay | — | Non utilisé | État local sidebar | Drawer + Overlay Manager |
| Sidebar mobile | même bouton | Unique contrôle | Conflit | Contrôle distinct contenu (`.ps-shell__open-product-nav`), hors topbar |

## Trois navigations

1. **Hamburger** → menu global ELFIS (plateforme + apps + déconnexion)
2. **Applications (Launcher)** → changer de Pilot
3. **Sidebar produit** → navigation interne Compta / Sales / Platform

## Structure du menu

- Accueil → `/home`
- Plateforme : Organisation, Membres, Relations, Documents, Communications, Aura, Paramètres
- Applications : ComptaPilot `/dashboard`, SalesPilot `/sales`
- Support : Aide (`/home#home-status`), Déconnexion

## Composants

- `platform-shell/global-nav/GlobalNavigationDrawer.tsx`
- `platform-shell/global-nav/globalNavModel.ts`
- `design-system/overlays/Drawer` (réutilisé)
- `closeChromeMenus` + `closeAllOverlays` pour exclusivité

## Permissions

Mapping temporaire permissions org existantes. Minimum toujours visible : Accueil, Applications, Aide, Déconnexion.

## Accessibilité

- `aria-label` dynamique : « Ouvrir le menu ELFIS » / « Fermer le menu ELFIS »
- `aria-expanded` / `aria-controls="elfis-global-navigation"`
- Drawer `role="dialog"` + nav intérieure
- Escape, overlay, X, retour focus hamburger
- Zones tactiles ≥ 44 px

## Responsive

- Desktop : un seul hamburger topbar ; drawer ~360 px gauche
- Mobile : plein écran ; ouverture nav produit via bouton **Navigation** dans le contenu (pas un 2e hamburger)

## Tests

`global-navigation.s111.test.tsx` — ouverture, clavier, Escape, X, routes actives, sidebar produit préservée.

## Validation manuelle

Voir tableau GN01–GN20 dans le rapport S1.1 mis à jour — **À tester manuellement**.
