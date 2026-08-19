# P2.3.1 — Stabilisation navigation plateforme & identité produit

**Date :** 2026-08-01  
**Statut :** Livré — STOP (pas de P2.4)  
**Audit :** [navigation-product-identity-audit-v1.md](./navigation-product-identity-audit-v1.md)

---

## 1. Architecture cible (3 niveaux)

```
PLATFORM SHELL
  topbar navy, Launcher, lockup ELFIS → /home, search, org, notifs, profil
PRODUCT SHELL
  sidebar métier, accent tokens --pilot-*, ProductSidebar + adapters
PAGE MÉTIER
  contenu fonctionnel uniquement
```

| Couche | Contient | N’appartient pas |
|---|---|---|
| PlatformShell | Chrome global, retour Home, org switcher | ifs Compta/Sales, nav métier |
| ProductShell / nav | Identité + nav métier via config/adapters | org, profil, logout, Launcher, search globale |
| Page | Formulaires / listes métier | Chrome double |

---

## 2. Retour à ELFIS Home

- Contrôle unique : `PlatformBrandLockup` dans `PlatformTopBar`
- `to="/home"`, `aria-label="Retour à ELFIS Home"`
- `closeAllOverlays('route_change')` au clic
- **Pas** de `setCurrentProduct` — `RuntimeThemeSync` suit la route
- Visible sur toutes les routes produit ; mobile : mark visible, label masqué ≤900px
- Sur Home : `showProductIndicator: false` (lockup suffit)

---

## 3. Séparation des paramètres

| Entrée | Destination | Shell |
|---|---|---|
| Home « Paramètres » | `/platform/settings` | ELFIS Core |
| UserMenu « Paramètres ELFIS » | `/platform/settings` | ELFIS Core |
| Launcher footer Paramètres | `/platform/settings` | ELFIS Core |
| Compta nav « Comptabilité & OCR » | `/settings` | ComptaPilot |
| Sales nav Paramètres | `/sales/settings` | SalesPilot |
| Organisation / Compte / Abo / Équipe / Modules | routes dédiées | ELFIS Core (`ElfisHomeLayout`) |

### Route officielle Core

**`/platform/settings`** — hub (liens réels + placeholder Sécurité).  
`/settings` conservé pour le métier finance (legacy contrôlé, pas de redirect destructif).

### Migration UI

- `SettingsPage` : identité org en **lecture** + lien Organisation ; édition OCR/compta/e-mail conservée
- `navModel` Compta : plus d’entrées Organisation / Abonnement / Compte / Modules
- Données org : **pas de duplication** — lecture API inchangée pour PDF

---

## 4. Classification champs entreprise

| Champ | Classification | Décision |
|---|---|---|
| Nom commercial | PARTAGÉ MAIS GÉRÉ PAR PLATEFORME | UI `/organisation` |
| Raison sociale | PARTAGÉ MAIS GÉRÉ PAR PLATEFORME | idem |
| Forme juridique | PARTAGÉ MAIS GÉRÉ PAR PLATEFORME | idem |
| Capital social | PARTAGÉ MAIS GÉRÉ PAR PLATEFORME | idem |
| SIRET / SIREN | PARTAGÉ MAIS GÉRÉ PAR PLATEFORME | lecture Compta PDF OK |
| N° TVA | PARTAGÉ MAIS GÉRÉ PAR PLATEFORME | **pas de move aveugle** ; gestion UI Core ; `CompanySettings.vat_number` sync lecture |
| Adresse / CP / Ville / Pays | PARTAGÉ MAIS GÉRÉ PAR PLATEFORME | Organisation |
| Téléphone / E-mail / Site | PARTAGÉ MAIS GÉRÉ PAR PLATEFORME | Organisation |
| IBAN / BIC | PARTAGÉ MAIS GÉRÉ PAR PLATEFORME | UI Organisation ; usage PDF/facturation = lecture seule côté Compta |
| Mentions légales | PARTAGÉ MAIS GÉRÉ PAR PLATEFORME | Organisation |
| Logo | PARTAGÉ MAIS GÉRÉ PAR PLATEFORME | Organisation |
| Comptes OCR / seuils / comptes 606… | PRODUIT (Compta) | `/settings` |
| Pipelines CRM | PRODUIT (Sales) | `/sales/settings` |
| Sécurité sessions | PLATEFORME | placeholder hub |

---

## 5. Topbar

Hiérarchie : `[menu mobile][Apps][ELFIS Core→/home][produit actif][search][org][notifs][profil]`

- Navy partagée (`--platform-shell-bg`)
- Le produit **n’écrase pas** la marque plateforme

---

## 6. ProductSidebar partagé

Composants : `ProductSidebar`, `ProductSidebarHeader`, `ProductSidebarFooter`, `ProductNavigationSection`, `ProductNavigationItem`

- **Interdit** : `if productId === "comptapilot"` dans le shared
- Différences via `className` / config (`ps-product-nav--compta` / `--sales`)
- `ComptaProductNav` = adapter hiérarchique + trial
- `SalesProductNav` = items plats + lien switch temporaire

---

## 7. Identités produit

### ComptaPilot (vert soft, accessible)

- Surface : `--pilot-secondary` / gradient clair — **pas** sidebar full green
- Texte : `--pilot-primary` (#0B3D2E)
- Actif : surface soft + rail `inset 3px` primary
- Cause bug blanc/illisible : `.ps-sidebar` blanc + `.nav` texte mint (legacy dark) → corrigé par overrides `.ps-shell--compta`

### SalesPilot

- Accent bleu `--pilot-accent` / primary blue
- Surface soft blue ; pas de leftovers verts

---

## 8. UserMenu

ELFIS Home · Mon compte · Organisation · Paramètres ELFIS · Préférences · Déconnexion  
« Paramètres ELFIS » → **jamais** Compta `/settings`.

---

## 9. Home sidebar

Accueil / Favoris / Activité / Notifications / Paramètres→`/platform/settings`  
Aide : ancre `#home-status` (pas de route aide user — documenté ; pas de jump silencieux Pilot).

---

## 10. Routing & thème

`isPlatformShellPath` + `ProductAccessLayout` → `ElfisHomeLayout` pour Core.  
`resolveRuntimeProductFromPath` : `/organisation`, `/compte`, `/platform/*`, `/admin/*`, etc. → `elfis-core` ; `/settings` → `comptapilot`.

---

## 11. Responsive & a11y

- Burger + scrim mobile ; lockup Home toujours dans topbar
- `aria-label` Home ; `aria-current` NavLink ; focus-visible tokens
- États nav : normal / hover / active / focus / disabled / locked

---

## 12. Tests

Fichier : `frontend/src/platform-shell/navigation-product-identity.test.tsx` (22 items)  
Suites associées mises à jour (Home sidebar, launcher, platform-shell, thème).

**Résultat :** 51 tests ciblés OK · `tsc --noEmit` OK · `npm run build` OK

---

## 13. Checklist manuelle

- [ ] Depuis `/dashboard` : clic lockup ELFIS → `/home`, thème Core, overlays fermés
- [ ] Depuis `/sales` : même retour Home
- [ ] Home → Paramètres → hub `/platform/settings` (pas sidebar Compta)
- [ ] UserMenu → Paramètres ELFIS → hub Core
- [ ] `/organisation` sous shell Home (sidebar plateforme)
- [ ] Compta `/settings` : préférences finance ; identité en lecture + lien Organisation
- [ ] PDF / facturation : org data toujours lue (pas de régression génération)
- [ ] Sidebar Compta : contraste lisible, rail vert soft, pas full green
- [ ] Sidebar Sales : bleu, pas de vert
- [ ] Mobile ≤900px : burger, lockup (mark), menu produit
- [ ] Déconnexion → `/login`
- [ ] Launcher : footer Paramètres → `/platform/settings`
- [ ] Pas d’oscillation thème en naviguant Home ↔ Compta ↔ Sales

---

## 14. Dette / inventaire

| Élément | Statut |
|---|---|
| Classe legacy `sidebar` sur PlatformSidebar Compta | **Supprimé** (remplacé `ps-sidebar--compta`) |
| Entrées org/abo/compte dans nav Compta | **Migré** hors nav produit |
| Édition marque dans `SettingsPage` | **Migré** → lecture + Organisation |
| Route `/settings` | **Conservé temporairement** (métier finance) |
| Lien Sales « ← ComptaPilot » | **Conservé temporairement** |
| CSS `.sidebar` / `.nav` dark dans `index.css` | **Dette restante** (overrides shell ; nettoyage global différé) |
| Placeholder Sécurité hub | **Dette restante** |
| Aide & Support route dédiée | **Dette restante** |
| Redirect HTTP `/settings` → split total | Non fait volontairement (évite casser bookmarks finance) |

---

## 15. Fichiers clés

- `platform-shell/PlatformBrandLockup.tsx`
- `platform-shell/PlatformTopBar.tsx`, `UserMenu.tsx`, `ProductNavigation.tsx`
- `platform-shell/platformPaths.ts`, `platform-shell.css`
- `pages/PlatformSettingsPage.tsx`, `pages/SettingsPage.tsx`
- `components/layouts/ProductAccessLayout.tsx`, `WorkspaceLayout.tsx`
- `design-system/themes/resolveRuntimeProductFromPath.ts`
- `home/HomePlatformSidebar.tsx`, `navModel.ts`

---

## 16. STOP

**P2.3.1 terminé.** Pas de P2.4, pas de nouvelles features métier, pas de changements Firebase.
