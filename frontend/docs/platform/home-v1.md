# P2.1 — ELFIS Home V1

## Objectif

Après authentification, la destination par défaut est **ELFIS Home** (`/home`), pas ComptaPilot.

```
Landing → Login → /home → choix d’application → /dashboard | /sales | …
```

`/dashboard` et `/sales` restent les espaces de travail des Pilot — ils ne sont pas supprimés.

## Routes & navigation

| Chemin | Rôle |
|--------|------|
| `/home` | Hub plateforme (ElfisHomeLayout + PlatformShell `elfis-core`) |
| `/dashboard` | Workspace ComptaPilot |
| `/sales` | Workspace SalesPilot |

Redirects post-auth :

- Login (défaut) → `/home` (invite → `/compte`, `state.from` conservé si sûr)
- Landing authentifié → CTA `/home`
- Welcome (entitled) → `/home`
- Register déjà connecté → `/home`

## Module

```
src/home/
  ElfisHomeLayout.tsx   # PlatformShell sans sidebar métier
  ElfisHomePage.tsx     # Sections Home (mock activité / notifs)
  HomeAppCardView.tsx
  homeCatalog.ts
  lastProduct.ts        # localStorage dernière app (comptapilot | salespilot)
  home.css
```

## Sections Home

1. Bienvenue — Bonjour {prénom}, org, workspace, dernière connexion  
2. Continuer votre travail — grande carte reprise (dernière app)  
3. Vos applications — ComptaPilot, SalesPilot (+ Doc/HR/Analytics/Support grisés « Bientôt disponible »)  
4. Activité récente — chronologie mock  
5. Notifications — 5 dernières mock  
6. Statut plateforme — connexion / org / sync / version + « Tout fonctionne »

Aucune logique métier (pas d’API métier).

## Launcher Premium

Le bouton **Applications** (TopBar / PlatformLauncher) ouvre le même `AppLauncher` avec :

- panneau large (`app-launcher-popover--premium`)
- grille de cartes + descriptions
- animations légères (respect `prefers-reduced-motion`)
- logos / badges « Bientôt disponible »

À l’ouverture d’un Pilot, `setLastProductId` met à jour la reprise Home.

## Thème

`/home` → `resolveRuntimeProductFromPath` → `elfis-core` (surface platform, pas de persist).  
Pas de `setCurrentProduct` dans les layouts.

## Hors scope P2.1

- ComptaPilot / SalesPilot métier, CRM, Backend, Auth Firebase, Theme Engine (hors mapping path)
- DocPilot produit réel

## Qualité

- Responsive, focus visible, ARIA sur sections  
- Tests : `ElfisHomePage.test.tsx`, `lastProduct.test.ts`, `AppLauncherPanel.premium.test.tsx`, redirect login, path theme  
- TypeScript / build frontend
