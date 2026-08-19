# 14 — Relations shared view

## Surface

`/platform/relations` — projection lecture :

- clients (`/billing/customers`)
- fournisseurs (`contacts` type supplier)
- rôles affichés (Client ComptaPilot / Fournisseur)
- rapprochement heuristique e-mail / nom (pas de fusion)

## Vues métier conservées

| Vue | Route | Contenu |
|-----|-------|---------|
| Clients Compta | `/clients` | fiscalité, factures, solde + lien ELFIS |
| Fournisseurs Compta | `/fournisseurs` | achats / OCR + lien ELFIS |

## Non fait

- Fusion tables
- Party model unifié
- Dédoublonnage automatique

Documenté pour S1.2+ avec plan de migration validé.
