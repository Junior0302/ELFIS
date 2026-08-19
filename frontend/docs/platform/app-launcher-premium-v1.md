# App Launcher Premium V1 (P2.3)

**Statut** · Livré  
**Implémentation** · `frontend/src/app-launcher/`  
**Entrée shell** · `PlatformLauncher` → `AppLauncher`

---

## Architecture

```
PlatformLauncher (adapter)
└── AppLauncher (orchestrateur)
    ├── AppLauncherTrigger
    ├── Dialog (desktop) / Drawer (mobile)
    └── AppLauncherPanel
        ├── LauncherHeader
        ├── LauncherSearch
        ├── LauncherContinueCard
        ├── LauncherProductGrid → LauncherProductCard
        └── LauncherFooter

launcherState.ts     → résolution registry / routes / entitlements
launcherModel.ts     → Continuer, filtre, footer, capabilities
productEntryRoutes.ts → /dashboard, /sales uniquement
Product Registry     → source unique (+ capabilities, featuredInLauncher)
```

**Interdit** : `setCurrentProduct()` / `applyTheme()` depuis le launcher.  
La navigation `navigate(route)` laisse `RuntimeThemeSync` appliquer le thème.

---

## Desktop / tablet / mobile

| Viewport | Surface | Layout |
|----------|---------|--------|
| Desktop | Dialog centré ~960–1040px, max-height ~84vh | Overlay navy soft + blur ; body clair ; radius 22px |
| Tablet | Même Dialog, largeur fluide | Grille 2 colonnes |
| Mobile ≤1024 | Drawer bottom | Sticky header/search/footer ; cartes 1 col |

---

## Header

- Pilot Mark ELFIS Core
- Titre **Applications ELFIS**
- Sous-titre : *Accédez à toutes vos expertises depuis un seul espace.*
- Fond navy / gradient ; bouton fermer Dialog
- Corps du panneau : clair

---

## Search

- Locale uniquement : `Rechercher une application…`
- Filtre : nom, description, catégorie, capabilities, status
- Empty state, Effacer, autofocus (`initialFocusRef`)
- Escape ferme le launcher (Dialog/Drawer)
- Ctrl/Cmd+K **non** intercepté (réservé recherche globale)
- Ctrl/Cmd+Shift+A ouvre/ferme le launcher

---

## Continuer

- **Uniquement** `lastProduct` (`elfis_last_product`)
- Accent couleur produit
- Sinon : CTA *Commencer avec ComptaPilot* (pas d’historique inventé)

---

## Applications disponibles

Grandes cartes :

- Mark, nom, **by ELFIS Core**, description, jusqu’à 3 capabilities
- Status (active / beta / Ouvrir)
- ComptaPilot → `/dashboard` (vert)
- SalesPilot → `/sales` (bleu, beta en DEV / coming_soon en prod selon registry)
- Hover elevation / halo accent

---

## Coming soon

Cartes atténuées (featured registry) : DocPilot, HRPilot, SupportPilot (+ SalesPilot hors DEV).  
Autres Pilots registry : chips « À venir dans ELFIS ».  
Pas de navigation vers routes manquantes. Pas de dates fictives.  
AnalyticsPilot : Home-only, **absent** du registry → non listé ici.

---

## Footer

| Label | Route |
|-------|-------|
| ELFIS Home | `/home` |
| Gérer organisation | `/organisation` |
| Paramètres | `/settings` |
| Découvrir | `/modules` |

Aide & Support / Marketplace : **masqués** (pas de route user réelle).

---

## Navigation

1. Vérifier `canOpen` + route SPA  
2. `closeAllOverlays('product_change')`  
3. Fermer launcher  
4. `setLastProductId`  
5. `navigate(route)` → thème via RuntimeThemeSync  
6. Restore focus trigger

---

## A11y

- `aria-modal`, labelledby / describedby
- Focus trap Dialog/Drawer
- Return focus → bouton Applications
- Escape, Tab, Enter/Space
- Status accessibles (badges + aria-label)
- `prefers-reduced-motion`

---

## Motion

| Action | Durée |
|--------|-------|
| Open panel | ~210 ms |
| Backdrop | ~200 ms |
| Close | overlay manager (~140–200 ms) |
| Hover | ~160 ms |

---

## Analytics (buffer existant)

| Event | Usage |
|-------|-------|
| `app_launcher.opened` | Ouverture |
| `app_launcher.closed` | Fermeture |
| `app_launcher.searched` | Première recherche de session open |
| `app_launcher.product_selected` | Ouverture Pilot (= product_opened) |
| `app_launcher.unavailable_clicked` | Clic coming_soon / locked |
| `app_launcher.coming_soon_viewed` | Featured bientôt |

Pas de données sensibles. Pas de nouveau service.

---

## Dette retirée (P2.3)

| Supprimé | Conservé | À migrer plus tard |
|----------|----------|-------------------|
| `LegacyLauncherPanel` | `PlatformLauncher` adapter | `HOME_APP_CARDS` → registry |
| Section « récentes » inventée | `launcherState` / routes | AnalyticsPilot dans registry |
| Lien Marketplace | Dialog / Drawer overlays | Route Aide & Support user |
| Styles popover dropdown | Theme via route | — |

---

## Tests

- `launcherState.test.ts` — résolution, featured, entitlements
- `launcherModel.test.ts` — Continuer, filtre, footer
- `AppLauncherPanel.premium.test.tsx` — UI structure / search / lastProduct
- `app-launcher.integration.test.tsx` — open/close, Escape, focus, analytics, shortcut, mobile Drawer, sandbox

---

## Checklist validation manuelle

- [ ] Ouvrir depuis `/home`, `/dashboard`, `/sales` (bouton Applications)
- [ ] Fermer : bouton ×, Escape, clic backdrop
- [ ] Focus : trap dans panel ; retour sur Applications
- [ ] Recherche : filtre + empty + Effacer
- [ ] Continuer : lastProduct réel ; sinon Commencer ComptaPilot
- [ ] Cartes ComptaPilot / SalesPilot (DEV) avec capabilities
- [ ] Coming soon : Doc / HR / Support — pas de nav
- [ ] Ouvrir Compta → `/dashboard` ; Sales → `/sales` ; thème via route (pas apply direct)
- [ ] Footer : Home, Org, Settings, Découvrir uniquement
- [ ] Mobile : Drawer quasi plein, 1 col, pas d’overflow horizontal
- [ ] Zoom 200 % lisible
- [ ] `prefers-reduced-motion` : pas d’anim intrusive
- [ ] Ctrl/Cmd+Shift+A ; Ctrl/Cmd+K inchangé (recherche)
- [ ] DEV : Sales ouvrable ; build prod : Sales coming_soon si registry le dit

---

## Notes runtime

- SalesPilot : `beta` + `availableInLauncher` en DEV ; `coming_soon` en production (inchangé).
- Un seul chemin officiel : Home / Compta / Sales / futurs Pilots via Platform Shell.
- TS / Vitest / build : valider après merge local.

## Dette restante

1. Unifier `HOME_APP_CARDS` avec le Product Registry  
2. Décider du statut prod SalesPilot (platform, hors P2.3 métier)  
3. Route Aide & Support utilisateur  
4. P2.4 (hors scope)
