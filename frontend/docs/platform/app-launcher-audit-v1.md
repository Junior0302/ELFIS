# App Launcher — Audit V1 (P2.3)

**Date** · 2026-08-01  
**Périmètre** · Signature launcher plateforme ELFIS (Premium V1)  
**Hors scope** · Métier Compta/Sales, Theme Engine apply, Marketplace, P2.4, backend

---

## Matrice d’audit

| Élément | État actuel | À conserver | À remplacer | Risque | Solution |
|--------|-------------|-------------|-------------|--------|----------|
| `PlatformLauncher` | Adapter mince → `AppLauncher` | Adapter officiel unique | — | Faible | Garder ; documenter comme point d’entrée shell |
| `AppLauncher` | Dialog desktop + Drawer mobile, analytics open/close/select | Orchestration, overlays, navigate | Panel legacy, structure « récentes » inventées | Moyen | Évoluer en Premium V1 (Continuer réel, header navy, footer routes réelles) |
| `AppLauncherPanel` | Premium partiel (`premium-v2`) + `LegacyLauncherPanel` | Composition panel | Legacy + section « Applications récentes » filler | Moyen | Découper Header/Search/Continue/Grid/Footer ; supprimer Legacy |
| `AppLauncherProductCard` | Carte Mark + titre + badge + tagline | Mark, accent, a11y clavier | Manque capabilities, « by ELFIS Core », CTA Ouvrir | Faible | `LauncherProductCard` enrichie |
| `AppLauncherTrigger` | Bouton « Applications » topbar | Trigger + aria | — | Faible | Ajouter `ref` pour restore focus ; raccourci Ctrl/Cmd+Shift+A |
| `launcherState` | Résolution pure registry + routes + entitlements | Source vérité états | `LAUNCHER_FEATURED_COMING_SOON` figé sales+doc | Faible | Featured via métadonnées / liste doc/hr/support (+ sales si coming_soon) |
| `productEntryRoutes` | `/dashboard`, `/sales` réels ; null ailleurs | Unique map routes SPA | — | Faible | Conserver ; jamais `websitePath` |
| Product Registry | Identités, status, couleurs, `availableInLauncher` | Source unique produits | Capabilities absentes du registry (Home a un catalog parallèle) | Moyen | Ajouter `capabilities` (+ flags launcher) sans 2ᵉ registry |
| `HOME_APP_CARDS` | Catalog Home parallèle (capabilities, AnalyticsPilot) | Cartes Home P2.2 | Duplication liste produits | Moyen | Launcher ne consomme **pas** homeCatalog ; debt Home → registry plus tard |
| `lastProduct` | localStorage Compta/Sales | Continuer réel | — | Faible | Section Continuer = `getLastProductId()` uniquement ; pas d’historique inventé |
| `ProductThemeProvider` | Thème via route / RuntimeThemeSync | Route = source de vérité | Apply thème depuis launcher | **Haut** | Ne jamais appeler `setCurrentProduct` / `applyTheme` depuis launcher |
| `OverlayProvider` / Dialog / Drawer | Focus trap, Escape, backdrop, `closeAllOverlays` | A11y overlay | Dropdown/Popover launcher | Faible | Dialog centré 960–1100px ; mobile Drawer ; `returnFocusRef` |
| Popover launcher | CSS `.app-launcher-popover` mort (petit dropdown) | — | Styles dropdown | Faible | Retirer styles dropdown inutilisés |
| Routes produit | `/dashboard`, `/sales` | Navigation réelle | Routes manquantes coming_soon | Faible | `canOpen` seulement si route SPA connue |
| Status active / beta / coming_soon | Registry + validate | Règles validate | SalesPilot DEV=beta / prod=coming_soon | Moyen | Respecter registry ; ne pas forcer Sales en prod |
| Entitlements | Supporté dans resolver si fourni | Branche locked | Pas de faux entitlements | Faible | Ne pas inventer ; UI locked si contexte présent |
| Org / footer | Marketplace disabled, Org, Settings, Compte | Org, Settings | Marketplace faux, Compte hors brief | Faible | Footer : Home, Org, Settings, Découvrir (`/modules`) ; masquer Aide (pas de route user) |
| Responsive | Dialog + Drawer ≤1024 | Breakpoints | Grille / sticky header mobile à peaufiner | Faible | Desktop centré ; tablet 2-col ; mobile 1-col Drawer |
| Clavier / focus | Escape Dialog ; Enter/Space cartes | Focus trap overlay | Autofocus search, restore trigger, Ctrl+Shift+A | Moyen | `initialFocusRef` search ; `returnFocusRef` trigger ; shortcut sans voler Ctrl+K |
| Animations | Enter ~280ms, hover 150ms, reduced-motion | Motion CSS léger | Timing hors brief (open 180–240) | Faible | Ajuster 200–220 ms open / 160 ms close ; prefers-reduced-motion |
| Analytics buffer | `opened`, `closed`, `product_selected`, `coming_soon_viewed` | Buffer existant | Manque searched / unavailable | Faible | Ajouter `searched`, `unavailable_clicked` ; garder `product_selected` (= product_opened) |
| Tests | Unit + integration + premium panel | Couverture base | Assertions « récentes » / Marketplace | Moyen | Réécrire pour Continuer / Available / Coming soon / nav / a11y |
| Doublons launcher | Un seul chemin `PlatformLauncher` → `AppLauncher` | — | Legacy panel interne | Faible | Supprimer Legacy ; documenter dette Home catalog |

---

## Dette documentée

| Statut | Élément |
|--------|---------|
| **Conservé** | `PlatformLauncher` adapter, `AppLauncher` orchestrateur, `launcherState`, `productEntryRoutes`, Dialog/Drawer, Product Registry, `lastProduct`, Theme via route |
| **Supprimé (P2.3)** | `LegacyLauncherPanel`, section « Applications récentes » inventée, lien Marketplace, styles popover dropdown |
| **À migrer plus tard** | `HOME_APP_CARDS` → registry unique ; AnalyticsPilot (hors registry) ; Aide & Support (route user) ; Theme Engine apply from launcher (interdit P2.3) |

---

## Décision d’architecture

Évoluer **`frontend/src/app-launcher/`** comme implémentation officielle Premium V1.  
`PlatformLauncher` reste l’adaptateur shell. Pas de second dossier `platform-shell/launcher/` (évite duplication).
