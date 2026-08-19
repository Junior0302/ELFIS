# Audit P2.3.1 — Navigation plateforme & identité produit

**Date :** 2026-08-01  
**Scope :** PlatformShell, ProductShell, Home, Settings, identité Compta/Sales  
**Statut :** Audit avant corrections — sources exactes des 3 régressions principales

---

## 1. Matrice problèmes

| Problème | Cause exacte | Composant | Responsabilité correcte | Correction | Risque |
|---|---|---|---|---|---|
| Pas de retour clair vers ELFIS Home | `ProductIndicator` est un `<div>` non cliquable ; aucun lockup ELFIS Core → `/home` dans la topbar ; `UserMenu` sans entrée Home | `ProductIndicator`, `PlatformTopBar`, `UserMenu` | PLATFORM SHELL | Lockup/logo ELFIS Core cliquable → `/home` (`aria-label="Retour à ELFIS Home"`), fermeture overlays, sans `setCurrentProduct` | Faible — surface chrome uniquement |
| Paramètres depuis Home ouvre ComptaPilot | Home → `to: "/settings"` ; `ProductAccessLayout` catch-all → `WorkspaceLayout` (Compta) ; `/settings` listé dans `COMPTAPILOT_PREFIXES` | `HomePlatformSidebar`, `ProductAccessLayout`, `resolveRuntimeProductFromPath`, `App.tsx` | PLATFORM vs PRODUCT | Route officielle `/platform/settings` ; Home/UserMenu → Core ; Compta `/settings` = finance only | Moyen — liens legacy `/settings` |
| Org / users / abo sous shell Compta | `/organisation`, `/compte`, `/abonnement`, `/admin/equipe` hors `/home` et `/sales` → `WorkspaceLayout` ; `navModel` catégorie Paramètres Compta | `ProductAccessLayout`, `navModel`, `OrganisationPage`, `SettingsPage` | ELFIS Core (données partagées) | Routes plateforme sous layout Core ; retirer gestion UI globale de la nav Compta ; lecture org conservée pour PDF | Moyen — facturation lit encore org |
| Sidebar Compta quasi blanche / illisible | `.ps-sidebar { background: #fff }` + classe legacy `.sidebar` ; styles `.nav a` pensés pour fond vert foncé (texte mint clair) → contraste cassé sur fond blanc | `platform-shell.css`, `index.css` `.sidebar`/`.nav`, `WorkspaceLayout` (`sidebarClassName="sidebar"`) | PRODUCT SHELL (tokens) | Surface soft green + texte foncé + rail actif via `--pilot-*` ; **pas** sidebar full green | Faible/moyen — CSS legacy |
| PlatformShell écrase identité produit | Topbar `--ps-card` blanc + sidebar blanche partagée ; accent Compta seulement sur `--ps-accent` sans surface nav | `platform-shell.css`, `PlatformShell` | Topbar = platform navy ; sidebar produit = accent | Séparer chrome topbar / surface produit | Faible |
| Séparation Core / Produit / Page floue | Routes plateforme montées dans shell Compta ; `SettingsPage` mélange marque org + OCR/TVA ; `UserMenu` « Préférences » → `/settings` Compta | Routing + pages settings | 3 niveaux stricts | Layout plateforme + split settings + UserMenu | Moyen |
| Pas de brand platform dans topbar | Hiérarchie demandée `[Apps][ELFIS→/home][produit]` absente ; seul le produit est affiché | `PlatformTopBar` | PLATFORM | Ajouter `PlatformBrandLockup` avant `ProductIndicator` | Faible |
| ProductSidebar non unifié | Sales utilise `ProductSidebar` ; Compta a `ComptaProductNav` ad-hoc + CSS `.sidebar` | `ProductNavigation`, `ComptaProductNav`, `SalesProductNav` | Shared + adapters | Header/Footer/Item partagés ; config, **zéro** `if productId` dans shared | Moyen — nav Compta hiérarchique |
| Aide Home → ancre status | `#home-status` sans page aide réelle | `HomePlatformSidebar` | PLATFORM | Documenter placeholder / lien réel si existant | Faible |
| IBAN/BIC/TVA dans pages Compta | Champs org édités dans `SettingsPage` + `OrganisationPage` sous shell Compta | Pages + API org | PARTAGÉ MAIS GÉRÉ PAR PLATEFORME | UI gestion → Core ; lecture métier inchangée | Élevé si move aveugle — **ne pas casser PDF** |

---

## 2. Trois régressions principales — causes racines

### R1 — Impossible de revenir clairement à `/home`

**Source exacte :**  
Après P2.3, le chrome unifié expose `ProductIndicator` (mark + nom Pilot + « by ELFIS Core ») comme élément **non interactif**. Aucun contrôle topbar ne navigue vers `/home`. Le Launcher contient « ELFIS Home », mais ce n’est pas un contrôle permanent visible. `UserMenu` n’a pas d’entrée « ELFIS Home ».

**Fichiers :**  
`ProductIndicator.tsx`, `PlatformTopBar.tsx`, `UserMenu.tsx`

### R2 — « Paramètres » depuis ELFIS Home ouvre les paramètres ComptaPilot

**Source exacte :**  
1. `HomePlatformSidebar` : `{ id: 'settings', to: '/settings' }`  
2. `ProductAccessLayout` : seuls `/home*` et `/sales*` ont un layout dédié ; tout le reste (dont `/settings`) tombe dans `WorkspaceLayout` (Compta)  
3. `resolveRuntimeProductFromPath` : `'/settings'` ∈ `COMPTAPILOT_PREFIXES` → thème ComptaPilot  

**Fichiers :**  
`HomePlatformSidebar.tsx`, `ProductAccessLayout.tsx`, `resolveRuntimeProductFromPath.ts`, `App.tsx` (route `settings` sous Layout produit)

### R3 — Paramètres organisation encore sous Compta alors qu’ils appartiennent à ELFIS Core

**Source exacte :**  
Même catch-all layout que R2 pour `/organisation`, `/compte`, `/abonnement`, `/admin/equipe`. De plus `navModel` expose la catégorie « Paramètres » Compta avec Entreprise (`/organisation`), Préférences (`/settings`), Abonnement, Compte, Modules. `SettingsPage` édite à la fois l’identité légale org (partagée PDF) **et** les préférences comptables OCR/TVA.

**Fichiers :**  
`navModel.ts`, `OrganisationPage.tsx`, `SettingsPage.tsx`, `ProductAccessLayout.tsx`

---

## 3. Inventaire composants (audit)

| Zone | Fichiers clés | Constat |
|---|---|---|
| PlatformShell | `PlatformShell.tsx` | OK — pas d’ifs Compta/Sales ; chrome via config |
| PlatformTopBar | `PlatformTopBar.tsx` | Manque lockup Home ; hiérarchie incomplète |
| PlatformSidebar | slot dans TopBar | Fond blanc générique — écrase identité |
| ProductIndicator | `ProductIndicator.tsx` | Affiche produit actif ; ne remplace pas le brand platform |
| ProductShellConfiguration | `productShellConfig.ts` | Contrat chrome OK ; homeRoute Compta=`/dashboard` (produit, pas platform) |
| WorkspaceLayout | Compta + PlatformShell | `sidebarClassName="sidebar"` réactive legacy dark-nav CSS |
| SalesWorkspaceLayout | Sales + PlatformShell | Utilise ProductSidebar partagé — OK |
| ComptaProductNav | Nav hiérarchique + trial | Métier OK ; styles legacy incompatibles fond clair |
| SalesProductNav | ProductSidebar | OK ; lien « ← ComptaPilot » à conserver temporairement |
| /home | `ElfisHomeLayout`, `HomePlatformSidebar` | Sidebar Core ; Paramètres → mauvais target |
| Settings | `SettingsPage`, `SalesSettingsPage` | Mixte Core+Compta ; Sales placeholder OK |
| UserMenu | Profil / Org / Préférences→`/settings` | Pas Home ; Préférences = Compta |
| OrganizationSwitcher | Topbar | OK plateforme |
| Launcher | P2.3 Premium | Contient ELFIS Home ; ne remplace pas lockup topbar |
| Theme Engine | `resolveRuntimeProductFromPath` | `/settings`, `/organisation` → comptapilot à tort |
| Legacy CSS | `index.css` `.sidebar`/`.nav` | Pensé fond vert foncé ; conflit `.ps-sidebar` |
| Nav active | `aria-current` partiel via NavLink | À renforcer ; états locked trial OK Compta |
| Permissions | `navModel` + membership | Conservées |
| Responsive | `platform-shell.css` mobile scrim | Menu burger OK ; Home return doit rester accessible |
| Overlays | `closeAllOverlays` (Launcher) | À appeler aussi sur navigation Home |

---

## 4. Architecture cible (rappel)

```
1. PLATFORM SHELL — topbar, Launcher, search, org, notifs, profil, retour Home
2. PRODUCT SHELL  — identité produit, sidebar métier, accent, nav produit
3. PAGE MÉTIER    — contenu fonctionnel uniquement
```

- PlatformShell : **interdit** ifs Compta/Sales  
- ProductShell / nav produit : **interdit** org, profil, logout, Launcher, search globale, notifs globales  

---

## 5. Décision route settings (pré-implémentation)

| Route | Rôle |
|---|---|
| `/platform/settings` | **Officiel** — paramètres ELFIS Core (hub) |
| `/organisation` | Core — identité org (layout plateforme) |
| `/compte` | Core — compte utilisateur |
| `/settings` | **Legacy Compta** — préférences finance/OCR ; sections marque → liens Core ; redirect documenté si besoin |
| `/sales/settings` | Sales — CRM only (placeholder existant) |

Home + UserMenu « Paramètres ELFIS » → **toujours** `/platform/settings`.

---

## 6. Classification champs entreprise (préliminaire — détail livraison)

Voir doc livraison § Enterprise fields. Principe : données communes multi-Pilots → **gérées UI par ELFIS Core** ; lecture métier autorisée (PDF, factures). IBAN/BIC/TVA : **PARTAGÉ MAIS GÉRÉ PAR PLATEFORME** après vérif usage — pas de duplication backend.

---

## 7. Hors scope (STOP)

- Pas de P2.4  
- Pas de nouvelles features métier  
- Pas de changements Firebase  
- Pas de duplication données org  
- Pas de seconde topbar / second PlatformShell  
