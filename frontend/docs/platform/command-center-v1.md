# ELFIS Command Center V1 (P2.4)

**Statut** · Livré  
**Implémentation** · `frontend/src/platform-command/`  
**Entrée shell** · `PlatformSearch` → `CommandCenter`

---

## Objectif

Point d’entrée universel de la plateforme : rechercher, naviguer ou lancer une action.  
**UX uniquement** — Search Engine V1 (`api.searchElfis`) reste la seule source de vérité pour les entités indexées. Aucun second moteur / indexation.

---

## Architecture

```
PlatformSearch (adapter TopBar)
└── CommandCenter (orchestrateur + ⌘K)
    ├── Trigger .ps-search__trigger
    └── Dialog (desktop ~960px / mobile fullscreen)
        └── CommandCenterPanel
            ├── CommandCenterHeader (Pilot Mark + titre)
            ├── CommandInput
            ├── RecentSearches
            ├── CommandResults → ResultGroup → ResultItem
            ├── EmptyState
            └── SearchFooter

commandModel.ts           → apps, nav, quick actions, command mode, grouping
useCommandSearch.ts       → debounce + api.searchElfis (Search Engine V1)
recentSearchesStorage.ts  → localStorage max 5
```

**Interdit** : nouveau backend search, Marketplace, IA, Agents, Workflow, Theme Engine depuis le CC, logique métier Compta/Sales.

---

## Ouverture

| Surface | Comportement |
|---------|----------------|
| Desktop / tablet | Dialog centré 900–1000px, overlay soft + blur, anim douce |
| Mobile ≤1024 | Dialog fullscreen |
| TopBar | Clic « Rechercher… » |
| Clavier | **Ctrl/Cmd+K** (ne vole pas Ctrl/Cmd+Shift+A du Launcher) |
| Fermeture | Escape, backdrop, navigation |

Header : Pilot Mark ELFIS Core · **ELFIS Command Center** · *Recherchez, naviguez ou lancez une action.*  
Input autofocus : *Que souhaitez-vous faire aujourd’hui ?*

---

## Sections

| Groupe | Source |
|--------|--------|
| Applications | Routes réelles (`/dashboard`, `/sales`) |
| Navigation | `/home`, `/platform/settings`, `/organisation` |
| Clients / Documents / Factures | Hits Search Engine V1 (`customer`, `vault_document`, `accounting_*`…) |
| Prospects / Opportunités | Affichés si le moteur renvoie des types mappés (sinon absents) |
| Commandes rapides | Suggestions locales par mots-clés |
| Commandes | Mode `>` uniquement |

---

## Recherche (Search Engine V1)

- Client : `api.searchElfis` via `useCommandSearch` (debounce 280 ms, min 2 caractères)
- Pas d’appel en mode commande
- Lien footer « Recherche complète » → `/search?q=…` (SearchPage existante)
- `action_url` du hit privilégié pour la navigation

---

## Quick actions (routes existantes)

| Mot-clé | Actions |
|---------|---------|
| facture | Nouvelle facture → `/facturation` · Factures → `/facturation` · Importer → `/deposit` |
| client | Nouveau client / Tous les clients → `/clients` |
| sales | Ouvrir SalesPilot → `/sales` |

---

## Mode commande (`>`)

Préfixe `>` → suggestions navigables uniquement (pas d’exécution métier) :

- `> nouvelle facture` → `/facturation`
- `> ouvrir salespilot` → `/sales`
- `> ouvrir comptapilot` → `/dashboard`
- `> importer document` → `/deposit`

---

## Recherches récentes

- Clé `elfis_command_center_recent`, max 5, effaçables
- Les commandes `>` ne sont pas persistées

---

## Clavier & a11y

- ↑ ↓ Entrée Escape ; Tab/Shift+Tab via focus trap Dialog
- Autofocus input ; restauration focus trigger à la fermeture
- `role="combobox"` / `listbox` / `option` ; labels FR
- `prefers-reduced-motion` : animations coupées
- Overlay design-system (scroll lock, Escape top overlay)

---

## Analytics (`productEvents`)

| Événement | Quand |
|-----------|--------|
| `command_center.open` | Ouverture |
| `command_center.search` | Première requête ≥2 car. (longueur seule, pas le texte) |
| `command_center.navigate` | Sélection (kind, group, href) |
| `command_center.close` | Fermeture |

Pas de PII / pas de nouveau service analytics.

---

## Design

Seconde signature après App Launcher : header navy + corps clair, radius ~22px, ombres douces, accent `#3d7eff`. Pas d’esthétique terminal.

---

## Tests

| Fichier | Couverture |
|---------|------------|
| `commandModel.test.ts` | Mode commande, quick actions, grouping SE V1 |
| `recentSearchesStorage.test.ts` | localStorage max 5 |
| `command-center.integration.test.tsx` | Ouverture, ⌘K, SE V1 mock, Escape, analytics |
| `platform-shell.test.tsx` | Trigger TopBar → Command Center |

---

## Dette restante

- Types Prospects / Opportunités côté index Search Engine (sections vides tant qu’absents)
- DocPilot sans route d’entrée → non listé en Applications
- `aria-activedescendant` dynamique (navigation clavier visuelle OK)
- Drawer bottom optionnel (V1 = Dialog fullscreen mobile)
- Pas de P2.5
