# 07 — Rapport d’implémentation S1.0

## Décisions appliquées

- Propriété : Core / Sales / Compta selon matrice 01  
- Aucune migration de tables  
- Aucune duplication de données  
- Parcours Client → Devis → Facture **conservé** (mêmes URLs)  
- Orchestrator : facture définitive reste Compta (doc uniquement)

## Navigation déplacée / clarifiée

| Avant | Après |
|-------|-------|
| Menu « Ventes » | **Facturation** |
| Pilotage | **Finance** |
| Documents | **Documents comptables** |
| Assistant | **Assistant financier** |
| Devis / Catalogue / Activités | Badges **→ SalesPilot** |
| Clients / Fournisseurs | Badges **ELFIS Core** |
| Équipe (Relations) | **Équipe & membres** → `/platform/settings` |
| — | Lien Aura / Tous documents → `/home` (placeholder Core) |
| Sales sidebar | Hint cycle commercial + ← ELFIS Home |

## Routes conservées

`/dashboard`, `/facturation`, `/devis`, `/catalogue`, `/activites`, `/clients`, `/fournisseurs`, `/documents`, `/settings`, `/admin/equipe`, `/sales/*`, `/home`, `/platform/settings`

## Redirects créés

`/quotes` → `/devis`  
`/catalog` → `/catalogue`  
`/sales/catalog` → `/catalogue`  
`/sales/quotes` → `/devis`  
`/team` → `/platform/settings`

## Données non migrées

customers, suppliers/contacts, invoices/quotes, vault objects, memberships — **inchangés**.

## Dette restante

Voir [06-transition-backlog](./06-transition-backlog.md).

## Risques

| Risque | Mitigation S1.0 |
|--------|-----------------|
| Confusion deux « Activités » | Chemins distincts documentés |
| Devis encore sous shell Compta | Badge + redirects futurs |
| `/home` pour Aura/docs | Placeholder explicite |
| Layout org encore Compta | Hub settings ; page legacy OK |

## Tests / build

- `navModel.test.ts` (libellés S1.0)  
- suites shell / launcher existantes  
- `tsc` + `npm run build`

## Proposition S1.1

Hub Relations Core + Devis/Catalogue sous shell Sales + filtre Documents comptables — **sans** casser l’envoi facture.

## Critère de fin S1.0

| Critère | Statut |
|---------|--------|
| Rôles Compta / Sales / Core clairs dans la nav | Oui |
| Parcours critique non cassé | Oui |
| Pas de duplication donnée | Oui |
| Pas de migration irréversible | Oui |
| Routes legacy compatibles | Oui |
| S1.1 non démarré | Oui |
