# 02 — Classification des écrans actuels

Sources : `navModel.ts`, `SalesProductNav`, `HomePlatformSidebar`, `App.tsx`.

## Légende

| Code | Signification |
|------|----------------|
| **RESTE** | Reste ComptaPilot |
| **→ SALES** | Migre SalesPilot (UI progressive) |
| **→ CORE** | Migre ELFIS Core |
| **VUE** | Vue filtrée conservée |
| **LATER** | À supprimer / fusionner plus tard |
| **?** | À confirmer |

## ComptaPilot (sidebar)

| Écran / entrée | Route | Classification | Note S1.0 |
|----------------|-------|----------------|-----------|
| Tableau de bord | `/dashboard` | RESTE | — |
| Factures (ex Vue d’ensemble Ventes) | `/facturation` | RESTE | Menu renommé Facturation |
| Devis | `/devis` | → SALES | Badge ; route legacy |
| Catalogue | `/catalogue` | → SALES | Alias `/catalog`, `/sales/catalog` |
| Activités | `/activites` | → SALES | ≠ `/sales/activities` |
| Finance / TVA / Clôture / Banque / Rapports | `/finance`… | RESTE | Libellé section Finance |
| Comptabilité * | `/accounting/*` | RESTE | — |
| Documents | `/documents` | VUE | « Documents comptables » ; Vault = Core |
| Importer / Migration | `/deposit`, `/migration` | VUE / ? | Import comptable reste Compta |
| Clients | `/clients` | VUE | Badge ELFIS Core |
| Fournisseurs | `/fournisseurs` | VUE | Badge ELFIS Core |
| Équipe | `/admin/equipe` | → CORE | Menu → `/platform/settings` |
| Assistant | `/copilote` | RESTE (contexte) | « Assistant financier » |
| Aura (lien) | `/home` | → CORE | Placeholder |
| Paramètres Compta | `/settings` | RESTE | Métier only |
| Organisation / abo / compte | routes legacy | → CORE | Via hub platform |

## SalesPilot

| Écran | Route | Classification |
|-------|-------|----------------|
| Dashboard / CRM / Pipeline / Proposals… | `/sales/*` | RESTE Sales |
| Paramètres | `/sales/settings` | RESTE Sales |

## ELFIS Home / Platform

| Écran | Route | Classification |
|-------|-------|----------------|
| Home | `/home` | RESTE Core |
| Platform settings hub | `/platform/settings` | RESTE Core |
| Launcher / Command Center | topbar | RESTE Core |

## Client / Fournisseur (nuance)

```
Party (ELFIS)
  ├── role: customer  → vue Compta (/clients)
  ├── role: supplier  → vue Compta (/fournisseurs)
  └── role: prospect  → Sales (/sales/leads)
```

S1.0 : **pas de fusion de tables** ; adapters futurs documentés dans 05.
