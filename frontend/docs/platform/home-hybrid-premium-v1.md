# P2.2.1 — ELFIS Home Hybrid Premium V1

## Objectif

Refactor **visuel uniquement** de `/home` vers une architecture hybride (~20 % surfaces sombres / ~80 % claires), sans changer la logique métier ni démarrer P2.3.

## Audit Home avant refactor (P2.2 Premium)

| Zone | État P2.2 | Constat |
|------|-----------|---------|
| Layout | `ElfisHomeLayout` + `PlatformShell` sans sidebar | Chrome plateforme, viewport plein largeur |
| Page | Monolithe `ElfisHomePage.tsx` | Hero, resume, apps, split activité/notifs, statut inline |
| Topbar | Claire (`ps-card`) | Identique Home / Compta / Sales |
| Sidebar | Absente sur Home | Nav métier uniquement sur Pilots |
| Hero | Texte + meta cards + mark discret | Pas de slot image dédié |
| Data | `homeCatalog` + `lastProduct` | Conservée |
| Marker | `data-home="premium-v2"` | Remplacé par `hybrid-premium-v1` |

## Architecture livrée

```
ElfisHomePage
├── HomePlatformSidebar          (via ElfisHomeLayout → PlatformShell)
├── HomeHero
│   ├── HomeContextCard ×3
│   └── HomeHeroVisual
├── ContinueWorkCard
├── HomeApplicationsGrid
│   └── HomeApplicationCard
├── RecentActivityPanel
├── HomeNotificationsPanel
└── PlatformStatusCard
```

Desktop :

```
TOPBAR SOMBRE (partagée)
SIDEBAR SOMBRE (Home only) | MAIN CLAIR (Hero, Resume, Apps) | RAIL CLAIR (Activité, Notifs, Status sombre)
```

Largeurs cibles : sidebar ~190px ; rail 330–390px ; max-width page ~1480px.

## Composants créés / modifiés

### Créés

- `HomePlatformSidebar.tsx` (+ test)
- `HomeHero.tsx`, `HomeContextCard.tsx`, `HomeHeroVisual.tsx`
- `ContinueWorkCard.tsx`
- `HomeApplicationsGrid.tsx`, `HomeApplicationCard.tsx`
- `RecentActivityPanel.tsx`, `HomeNotificationsPanel.tsx`
- `PlatformStatusCard.tsx`
- `homeConstants.ts` (`HOME_HERO_VISUAL_URL`)
- `public/branding/elfis/README.md` (slot image)

### Modifiés

- `ElfisHomePage.tsx` — orchestration hybride
- `ElfisHomeLayout.tsx` — sidebar Home + `ps-shell--home-hybrid`
- `home.css` — tokens / layout hybride
- `HomeAppCardView.tsx` — réexport compat
- `index.ts` — exports publics
- `ElfisHomePage.test.tsx` — assertions hybrid
- `platform-shell.css` — topbar sombre partagée

### Non touchés (volontairement)

- Métier ComptaPilot / SalesPilot
- Theme Engine (mapping/path)
- Landing, Login
- App Launcher (implémentation)
- Backend / Firebase

## Topbar sombre

- Tokens : `--platform-shell-bg #071426`, `--platform-shell-surface #0B1B30`, `--platform-shell-border rgba(255,255,255,.08)`.
- Appliquée via `.ps-shell > .ps-topbar` pour que **Home, Compta et Sales** partagent le même chrome.
- Composant `PlatformTopBar` inchangé (pas de topbar dupliquée).
- Accent Pilot via `--ps-accent` / Theme Engine existant.

## Sidebar sombre (Home uniquement)

Nav : Accueil, Favoris, Activité, Notifications, Paramètres.  
Bas : Aide & Support, Déconnexion, carte marque ELFIS Core.  
Drawer mobile via `PlatformShell` (burger + scrim).  
Ne remplace **pas** les navs produit Compta/Sales.

## Viewport clair

Fond dégradé doux (`#f3f6fa` → blanc). Hero, continue, apps, activité, notifications sur surfaces claires. Status plateforme en carte navy (accent sombre ~20 %).

## Hero + slot image

- Brand `ELFIS CORE`, salut, bienvenue, tagline, 3 context cards.
- `HOME_HERO_VISUAL_URL = "/branding/elfis/home-hero-visual.webp"`.
- Si fichier absent / erreur réseau → fallback Pilot Mark + halo + orbites SVG (pas d’image cassée, pas de base64).

## Continue card

Accent Pilot de la dernière app (vert Compta / bleu Sales). Activité réelle via `lastProduct` si présente ; sinon CTAs « Commencer avec ComptaPilot » / « Découvrir SalesPilot ».

## App cards 3×2

Six cartes (`HOME_APP_CARDS`) : ProductMark, description, 3 badges, statut, CTA. Coming soon grisées, sans faux liens. Hover ~170ms.

## Timeline / notifications / statut

- Timeline mock + badge **Aperçu** + lien « Voir toute l’activité ».
- Notifications mock + badge **Aperçu** (le centre topbar reste réel).
- Status sombre : Connexion, Org, Sync, Services, Version — « Tout fonctionne parfaitement » / « Aucun incident ». Org réelle ; pas de faux KPI.

## Responsive / a11y / motion

- Breakpoints ~1180 / 960 / 640 : stack rail, hero, grille apps.
- Focus visibles, roles/ARIA, labels nav, `prefers-reduced-motion`.
- Pas de lib lourde / particules.

## Tests / TS / build

À valider :

```bash
cd frontend
npx vitest run src/home src/platform-shell src/app-launcher src/design-system.runtime-theme.test.ts
npm run build
```

## Dette restante

- Asset `home-hero-visual.webp` non fourni (fallback actif).
- Favoris / Aide = ancres locales (pas de backend favoris).
- Timeline & notifs Home restent mock clairement labellisés.
- Densité rail sur très petits écrans à peaufiner en QA visuelle.
- P2.3 non démarré.
