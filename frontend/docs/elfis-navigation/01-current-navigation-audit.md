# 01 — Audit navigation actuelle (AVANT NAV.CORE.1)

## Constat

Trois sources de vérité pour la nav plateforme :

| Surface | Fichier | Structure |
|---------|---------|-----------|
| Drawer hamburger | `globalNavModel.ts` | Groupes plats home / platform / apps / support |
| Sidebar Home | `HomePlatformSidebar.tsx` | Liste plate inline `PRIMARY_NAV` |
| Sidebar workspace | `platformNavModel.ts` | Liste plate `PLATFORM_NAV_ITEMS` |

## Écarts observés

- Structure différente entre Home (Favoris, Activité, Notifications) et drawer (Aura, Membres, Apps Pilot).
- Pictogrammes dans Home uniquement ; absents du drawer.
- Branding visible « ELFIS Core » (drawer title, footer sidebars).
- Pas de sections Entreprise / Données / Plateforme / Outils.
- Apps ComptaPilot / SalesPilot dans le drawer (hors socle transversal — appartiennent au Launcher).

## Routes réelles inventoriées

| Destination | Route / ancre |
|-------------|----------------|
| Accueil | `/home` |
| Favoris | `/home#home-apps` |
| Activité | `/home#home-activity` |
| Organisation | `/platform/organization` |
| Membres | `/platform/members` |
| Rôles (légende) | `/platform/members#roles` (ancre sur page membres) |
| Relations | `/platform/relations` |
| Documents | `/platform/documents` |
| Notifications | `/notifications` |
| Communications | `/platform/communications` |
| Paramètres | `/platform/settings` |
| Intelligence (Aura) | `/platform/aura` |
| Recherche | `/search` |
| Aide | `/home#home-status` |

## Absents (pas de page user plateforme)

Contacts, Entreprises, Centre de santé, Journal — voir backlog doc 02.

