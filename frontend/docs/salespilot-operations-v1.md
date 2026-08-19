# SalesPilot Operations & Productivity V1 (S1.8)

## Philosophie

CRM utilisable toute la journée : saisie rapide, listes, filtres, vues, calendrier, import, doublons manuels. **Aucun** nouveau moteur IA. **Aucun** redesign Design System. **Aucun** sync calendrier externe.

## Audit (synthèse)

| Fonction | État avant S1.8 | Blocage | Solution retenue |
|----------|-----------------|---------|------------------|
| Leads / Companies / Contacts | Stubs `SalesEmptyPage` | Impossible de travailler | Listes CRUD + Quick Create |
| Tasks / Activities | Stubs | Idem | Listes + bulk mark_done |
| Notes | Create/list/delete | Pas d’édition | PATCH note |
| Quick Create | Absent | Navigation lourde | Drawer unifié DS |
| Saved Views | Absent | Refaire filtres | API + barre UI |
| Calendar | Absent | Pas de vue temps | Sales Calendar jour/semaine/mois |
| Import CSV | Absent | Saisie manuelle | Preview + commit |
| Doublons | Absent | Pollution data | Scan + ignore/link (manuel) |
| Journal | Absent | Pas d’historique perso | My Activity |
| Bulk | Absent | Actions 1 à 1 | Toolbar + ConfirmDialog |

## Frontend livré

- Pages listes : Leads, Companies, Contacts, Tasks, Activities
- `CrmResourceListPage` — recherche, pagination, sélection, bulk, Saved Views
- `QuickCreateDrawer` — Dashboard, Pipeline, Relationship, listes (brouillon localStorage)
- `SalesCalendarPage`, `SalesImportPage`, `SalesJournalPage`, `SalesDuplicatesPage`
- Routes + nav SalesPilot étendue
- DS 1.0 uniquement (Drawer, ConfirmDialog, PageHeader, …)

## Smart Forms (V1)

- Focus auto drawer
- Enter pour soumettre (champs titre)
- Anti double-soumission (`busy` + ref)
- Brouillon localStorage par type
- Messages d’erreur explicites
- Pré-remplissage contexte workspace (company / opportunity / entity)

## Limites assumées

- Filtres avancés (montant, health, tags) : stockés dans Saved Views ; application complète côté listes = `q` + status backend existants (extension progressive)
- Édition fiche complète = via workspace / deal (pas de formulaire parallèle)
- Menu contextuel clic droit : non (quick actions + sélection)
- Mentions @ : non (dette)
- Proposals liste : déjà S1.6 — ops s’appuie dessus

## Interdictions respectées

S1.9 non commencé. Pas de Google Calendar, Outlook, emails auto, assistant, analyse vocale.
