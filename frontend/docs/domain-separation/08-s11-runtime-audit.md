# 08 — S1.1 Runtime audit

Audit des surfaces réellement exécutées avant migration (non destructif).

| Surface | Route actuelle | Layout | Backend | Propriétaire actuel | Cible | Donnée | Risque | Stratégie |
|---------|----------------|--------|---------|---------------------|-------|--------|--------|-----------|
| Paramètres Core | `/platform/settings` | ElfisHome → PlatformWorkspace | Hub liens | ELFIS | ELFIS | Liens réels | Faible | Enrichir hub |
| Organisation | `/organisation` | Platform shell | `api.orgDetail` | Mixed UI | ELFIS | Réelle | Moyen | Redirect → `/platform/organization`, même page |
| Équipe | `/admin/equipe` | Platform shell | `api.orgMembers` | Mixed | ELFIS | Réelle | Moyen | Redirect → `/platform/members` |
| Documents Vault | `/documents` | Compta Workspace | `/vault/documents` | Compta UI | Split | Réelle | Moyen | Vue filtrée Compta + hub `/platform/documents` |
| Vault alias | `/vault` | Redirect | — | — | ELFIS | — | Faible | → `/platform/documents` |
| Communications | (pas de page user) | — | `listEmailConnections`, `platformEmailStatus` (admin) | Backend only | ELFIS | Réelle | Moyen | Nouvelle surface lecture sans secrets |
| Modèles e-mail facture | `/settings` | Compta | org email settings | Compta | Compta | Réelle | Faible | Rester Compta (métier) |
| Assistant financier | `/copilote` | Compta | `aiAssistantApi` | Compta | Compta contextual | Réelle | Faible | Renommer + lien Aura |
| Aura | absente | — | même moteur | — | ELFIS | Réutilise | Moyen | `/platform/aura` wrap moteur existant |
| Clients | `/clients` | Compta | `/billing/customers` | Compta | Vue métier | Réelle | Faible | Banner + lien Relations |
| Fournisseurs | `/fournisseurs` | Compta | `listContacts(supplier)` | Compta | Vue métier | Réelle | Faible | Banner + lien Relations |
| Relations unifiées | absente | — | customers + contacts | — | ELFIS | Projection | Moyen | Lecture sans fusion tables |
| Console admin | `/elfadmin/*` | PlatformLayout | `/platform/*` admin | Platform admin | Inchangé | Réelle | Élevé si conflité | Retirer catch-all `/platform/*` → elfadmin |
| Home | `/home` | ElfisHomeLayout | — | ELFIS | ELFIS | Réelle | Faible | Garder sidebar Home |
| Command Center | overlay | PlatformShell | Search V1 + catalogs | ELFIS | ELFIS | Mixte | Faible | Mettre à jour nav items |
| Launcher | overlay | PlatformShell | products | ELFIS | ELFIS | Réelle | Faible | Footer raccourcis plateforme |

## Conflit critique résolu

`App.tsx` redirigait `/platform` et `/platform/*` vers `/elfadmin` (RequirePlatformAdmin).  
S1.1 : workspace user sous `Layout` ; admin via `/elfadmin` et `/platform/admin`.

## Composants à réutiliser

- `OrganisationPage`, `AdminEquipePage`, `DocumentsPage`, `CopilotePage`
- `PlatformShell`, `listEmailConnections`, Vault API
- Pas de second backend / Vault / CRM / IA
