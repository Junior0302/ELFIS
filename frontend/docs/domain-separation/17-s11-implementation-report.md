# 17 — S1.1 implementation report

## Décisions appliquées

- Surfaces transverses migrées vers **ELFIS Core** sans migration DB
- `PlatformWorkspaceLayout` + `PlatformNavigation` distincts de Compta/Sales
- `/home` conserve `ElfisHomeLayout`
- Catch-all `/platform/*` → elfadmin **supprimé** (conflit résolu)
- Vault unique ; vue comptable = projection filtrée
- Aura = réutilisation moteur existant
- Relations = lecture unifiée sans fusion

## Surfaces migrées

| Surface | Route |
|---------|-------|
| Organisation | `/platform/organization` |
| Membres | `/platform/members` |
| Documents Vault | `/platform/documents` |
| Communications | `/platform/communications` (+ settings) |
| Aura | `/platform/aura` |
| Relations | `/platform/relations` |
| Settings hub | `/platform/settings` (enrichi) |

## Données réutilisées

`orgDetail`, `orgMembers`, Vault documents, `listEmailConnections`, `listCustomers`, `listContacts`, `aiAssistantApi`

## Composants créés

- `frontend/src/platform-workspace/*`
- `frontend/src/pages/platform-core/*`

## Redirects

`/organisation`, `/admin/equipe`, `/team`, `/vault`, `/platform/teams`, `/platform/roles`

## Temporaire dans ComptaPilot

- `/clients`, `/fournisseurs` (vues métier)
- `/documents` (filtrée)
- `/copilote` (assistant financier)
- `/settings` (OCR + modèles e-mail métier)
- Devis / catalogue / activités (transition SalesPilot — S1.0)

## Permissions

Mapping temporaire sur permissions existantes — dette `platform.*` en S1.2

## Tests

- Unitaires S1.1 : OK (voir 16)
- Validation manuelle M01–M20 : **À tester manuellement**

## Build

`tsc -b && vite build` : **OK** (2026-08-01)

## GO / NO GO

**GO conditionnel** — navigation et surfaces Core livrées ; validation manuelle Chris restante ; pas de migration irréversible.

## Dette S1.2 (ne pas démarrer ici)

- Permissions `platform.*` natives
- UI config e-mail complète dans Core
- Party model / fusion planifiée
- Aura contexte cross-Pilot
- Pages teams/roles dédiées
- Retrait progressif redirects legacy

**STOP — S1.2 non commencé.**

---

## S1.1.1 — Menu global ELFIS (follow-up)

### Cause

Hamburger masqué en desktop + callback = toggle sidebar produit uniquement.

### Livré

- Menu global Drawer gauche (Overlay Manager)
- Visible sur `/home`, Compta, Sales, `/platform/*`
- Toggle navigation produit mobile séparé
- Exclusivité avec Launcher / Command Center / UserMenu / Notifications
- Doc : `frontend/docs/platform/global-navigation-menu-v1.md`

### Tableau test manuel — Global Navigation

| ID | Route départ | Action | Attendu | Observé | Note | Statut | Capture | Commentaire |
|----|--------------|--------|---------|---------|------|--------|---------|-------------|
| GN01 | /home | Ouvrir hamburger | Drawer ELFIS | — | — | À tester manuellement | — | |
| GN02 | /dashboard | Ouvrir hamburger | Drawer ELFIS | — | — | À tester manuellement | — | |
| GN03 | /sales | Ouvrir hamburger | Drawer ELFIS | — | — | À tester manuellement | — | |
| GN04 | /platform/documents | Ouvrir hamburger | Drawer + Docs actif | — | — | À tester manuellement | — | |
| GN05 | menu | → Organisation | `/platform/organization` | — | — | À tester manuellement | — | |
| GN06 | menu | → Home | `/home` | — | — | À tester manuellement | — | |
| GN07 | menu | → Documents | `/platform/documents` | — | — | À tester manuellement | — | |
| GN08 | menu | → Communications | OK | — | — | À tester manuellement | — | |
| GN09 | menu | → Aura | OK | — | — | À tester manuellement | — | |
| GN10 | menu | → Relations | OK | — | — | À tester manuellement | — | |
| GN11 | menu | → ComptaPilot | `/dashboard` | — | — | À tester manuellement | — | |
| GN12 | menu | → SalesPilot | `/sales` | — | — | À tester manuellement | — | |
| GN13 | ouvert | Escape | Ferme + focus | — | — | À tester manuellement | — | |
| GN14 | ouvert | Overlay | Ferme | — | — | À tester manuellement | — | |
| GN15 | Launcher puis hamburger | Exclusivité | Un seul ouvert | — | — | À tester manuellement | — | |
| GN16 | hamburger puis Notifs | Exclusivité | Menu fermé | — | — | À tester manuellement | — | |
| GN17 | mobile | Drawer + nav produit | OK | — | — | À tester manuellement | — | |
| GN18 | navigateur | Retour | Historique OK | — | — | À tester manuellement | — | |
| GN19 | refresh | Deep link | Stable | — | — | À tester manuellement | — | |
| GN20 | menu | Déconnexion | Logout | — | — | À tester manuellement | — | |

**S1.2 non commencé.**
