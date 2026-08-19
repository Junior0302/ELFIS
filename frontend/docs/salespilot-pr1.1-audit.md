# SalesPilot PR1.1 — audit runtime & livrable

**Date :** 2026-07-26  
**Repo :** `C:\Users\Black\Desktop\elfis core`  
**Branche :** `main` @ `519df2b` (working tree local SalesPilot non commitée / ahead origin)  
**Scope :** Recette fonctionnelle & intégration E2E V1 — **aucune feature majeure nouvelle**, **pas de PR1.2**, **pas de Sales AI V2**.

---

## 1. Audit runtime

| Contrôle | Résultat |
|----------|----------|
| Branche | `main` |
| Commit HEAD | `519df2b` |
| Working tree | Nombreux changements locaux SalesPilot + plateforme |
| `import app.main` | OK (583 routes) |
| Routers inclus | `sales_crm`, `sales_proposals`, `sales_intelligence`, `sales_operations`, `sales_collaboration` sous `/api` |
| Env DEV | SalesPilot launcher = beta → `/sales` |
| Prod | SalesPilot = `coming_soon` |
| Health | `GET /api/health` |
| Seed | `python -m scripts.seed_salespilot_demo` |
| Migrations | `python -m scripts.apply_salespilot_migrations` |

---

## 2. Matrice fonctionnalités

| Fonctionnalité | Route FE | Composant | Endpoint BE | Router | Permission | État runtime | Blocage |
|----------------|----------|-----------|-------------|--------|------------|--------------|---------|
| Dashboard | `/sales` | `SalesDashboardPage` | `GET /api/sales/dashboard` | sales_crm | sales.read | branché | — |
| Prospects | `/sales/leads` | `SalesLeadsPage` | `/api/sales/leads` | sales_crm | sales.read/write | branché | — |
| Entreprises | `/sales/companies` | `SalesCompaniesPage` | `/api/sales/companies` | sales_crm | sales.* | branché | — |
| Contacts | `/sales/contacts` | `SalesContactsPage` | `/api/sales/people` | sales_crm | sales.* | branché | — |
| Pipeline | `/sales/pipeline` | `SalesPipelinePage` | `/api/sales/pipeline` | sales_crm | sales.* | branché | — |
| Workspace relation | `/sales/workspace/:entity/:id` | `RelationshipWorkspacePage` | CRM entity + workspace | sales_crm | sales.* | branché | — |
| Deal | `/sales/deals/:id` | `DealWorkspacePage` | deal endpoints | sales_crm | sales.* | branché | — |
| Propositions | `/sales/proposals` | `SalesProposalsPage` | `/api/sales/proposals` | sales_proposals | proposals.* | branché | — |
| Proposition new | `/sales/proposals/new` | `ProposalCreatePage` | POST proposals | sales_proposals | proposals.write | branché | — |
| Proposition WS | `/sales/proposals/:id` | `ProposalWorkspacePage` | workspace + bridge | sales_proposals | proposals.* | branché | Multi-TVA bloqué (Option B) |
| Tâches | `/sales/tasks` | `SalesTasksPage` | `/api/sales/tasks` | sales_crm | sales.* | branché | — |
| Activités | `/sales/activities` | `SalesActivitiesPage` | `/api/sales/activities` | sales_crm | sales.* | branché | — |
| Calendrier | `/sales/calendar` | `SalesCalendarPage` | `/api/sales/ops/calendar` | sales_operations | sales.read | branché | — |
| Journal | `/sales/journal` | `SalesJournalPage` | `/api/sales/ops/journal` | sales_operations | sales.read | branché | — |
| Intelligence | `/sales/intelligence` | `SalesIntelligencePage` | `/api/sales/intelligence` | sales_intelligence | sales.* | branché | — |
| Insight détail | `/sales/intelligence/:id` | `SalesInsightDetailPage` | `/insights/{id}` | sales_intelligence | sales.* | branché | — |
| Équipe | `/sales/team` | `SalesTeamDashboardPage` | `/api/sales/collab/team-dashboard` | sales_collaboration | sales.* | branché | — |
| Vues collab | `/sales/collab/views` | `SalesCollabViewsPage` | `/api/sales/collab/views` | sales_collaboration | sales.* | branché | — |
| Import | `/sales/import` | `SalesImportPage` | `/api/sales/ops/import/*` | sales_operations | sales.write | branché | — |
| Doublons | `/sales/duplicates` | `SalesDuplicatesPage` | `/api/sales/ops/duplicates/*` | sales_operations | sales.write | branché | — |
| Paramètres | `/sales/settings` | `SalesSettingsPage` | settings locaux | — | — | UI locale | — |
| Reports | `/sales/reports` | stub | — | — | — | hors nav | dette |

---

## 3–5. Navigation & App Launcher

- Sidebar : ordre PR1.1 FR ; Reports retiré ; Import/Doublons/Vues collab en secondaires.
- Pas de lien « Opportunités » inventé (Pipeline = board).
- Launcher : SalesPilot `/sales` en DEV beta ; `coming_soon` hors DEV ; `closeAll("product_change")` déjà câblé.

---

## 6–8. Seed, pipeline, migrations

- Seed DEMO idempotent + purge.
- Pipeline défaut : `defaults.py` (Prospection…Gagné/Perdu) + `ensure_default_pipeline` au provisioning workspace.
- Script migrations unique + rapport tables.

| Migration | Tables/colonnes | Appliquée via | Correctif |
|-----------|-----------------|---------------|-----------|
| CRM Foundation | sales_* CRM | create_all | SQL doc only |
| Proposals | sales_commercial_* | SQL + create_all | apply script |
| Bridge S1.6.1 | colonnes conversion | ALTER SQL | apply script |
| Intelligence S1.7 | sales_insight_items | SQL + create_all | apply script |
| Operations S1.8 | sales_saved_views | SQL + create_all | apply script |
| Collaboration S1.9 | teams/comments/… | SQL + create_all | apply script |

---

## 9–17. Surfaces validées (statut)

| Surface | Statut PR1.1 |
|---------|--------------|
| Dashboard | branché + seedable |
| Listes CRM | routes + API réelles |
| Quick Create | drawers existants (pas de nouvelle feature) |
| Pipeline | board + move API |
| Workspaces | relationship + deal |
| Cycle Proposal | flux API + UI ; multi-TVA bloqué |
| TVA multi-taux | **Option B** explicite |
| Intelligence | sync rules + seed data |
| Collaboration | teams/comments/followers/reviews |

---

## 18–21. Anomalies, smoke, E2E, manuel

- Anomalies : `frontend/docs/salespilot-pr1.1-anomalies.md`
- Smoke : `python -m scripts.smoke_salespilot`
- E2E : pas de Playwright ; procédure manuelle
- Manuel : `frontend/docs/salespilot-manual-test-v1.md`

---

## 22–24. Tests / build / dette

Exécuter localement :

```bat
cd backend
python -m unittest tests.sales_crm.test_proposal_invoice_bridge -v
python -m scripts.apply_salespilot_migrations --report-only
python -m scripts.smoke_salespilot

cd ../frontend
npx vitest run src/sales src/app-launcher src/authNetwork.test.ts src/LoginPage.test.tsx
npx tsc -b --pretty false
npm run build
```

**Dette restante :** Option A TVA multi-taux ComptaPilot ; Reports ; E2E Playwright ; UX équipe enrichie.

---

## 25. Confirmation

Aucune nouvelle feature majeure commencée. Pas de Sales AI V2. Pas de PR1.2. Arrêt après livrable PR1.1.
