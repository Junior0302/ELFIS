# 10 — Parité nav Commercial / Finance

Commercial utilise le **même pattern accordion** que Finance (`ComptaProductNav`) : catégories dépliables, chevron, parent actif si route enfant, flyout + tooltips en mode collapsed, accent Pilot (bleu Sales).

## Structure livrée → routes

| Catégorie | Entrées | Routes |
|-----------|---------|--------|
| Tableau de bord | (feuille) | `/sales` |
| Prospection | Prospects, Entreprises, Contacts, Import | `/sales/leads`, `/companies`, `/contacts`, `/import` |
| Pipeline | Vue d’ensemble, Propositions | `/sales/pipeline`, `/proposals` |
| Activités | Vue d’ensemble, Calendrier, Tâches, Journal | `/sales/activities`, `/calendar`, `/tasks`, `/journal` |
| Reporting | Vue d’ensemble, Performances | `/sales/reports`, `/intelligence` |
| Clients | Entreprises, Contacts, Relations | `/sales/companies`, `/contacts`, `/platform/relations` (badge ELFIS) |
| Paramètres | Général | `/sales/settings` |

## Omises (pas de page réelle — backlog)

| Entrée cible | Motif |
|--------------|--------|
| Prospection → Vue d’ensemble | Pas de hub dédié (entrée catégorie = Prospects) |
| Pipeline → Opportunités | Même surface que `/sales/pipeline` |
| Pipeline → Négociations / Gagnées | Pas de route |
| Activités → Appels / Emails | Pas de route |
| Reporting → Rapports | Doublon de Vue d’ensemble (`/sales/reports`) |
| Paramètres → Pipeline / Automatisations | Pas de sous-pages settings |
| Doublons / Team / Collab views | Hors menu (deep links conservés) |

Pas de badge « Bientôt » en nav (pattern launcher uniquement ; Finance utilise badge pour liens contextuels type ELFIS).

## Fichiers

- `frontend/src/sales/salesNavModel.ts` — modèle + `findActiveSalesCategory`
- `frontend/src/platform-shell/SalesProductNav.tsx` — accordion (miroir Compta)
- Styles : `platform-shell.css` (accent bleu), `unified-platform.css` (collapse)
- Tests : `sales-nav-expand.test.tsx`, suites ND / shell / e2e mises à jour

## Topbar

Inchangée : **Commercial / Moteur SalesPilot** (`ProductIndicator`).
