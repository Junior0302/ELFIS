# 04 — Plan de migration des routes

Convention : **ne pas inventer** de paths sans page. Alias legacy → routes réelles.

## Table

| Route actuelle | Route cible | Propriétaire | Redirect S1.0 | Compatibilité | Dette |
|----------------|-------------|--------------|---------------|---------------|-------|
| `/facturation` | `/facturation` | Compta | — | Indéfinie | Avoirs / récurrentes |
| `/devis` | `/sales/quotes` (futur) | Sales | `/quotes` → `/devis` | ≥ 2 versions | Page Sales dédiée |
| `/catalogue` | `/sales/catalog` | Sales | `/catalog`, `/sales/catalog` → `/catalogue` | ≥ 2 versions | Page sous Sales shell |
| `/activites` | `/sales/activities` | Sales | — (chemins distincts) | À clarifier | Unifier modèles |
| `/clients` | `/platform/relations/clients` | ELFIS | — | Jusqu’à hub Relations | Hub Relations |
| `/fournisseurs` | `/platform/relations/suppliers` | ELFIS | — | Idem | Idem |
| `/admin/equipe` | `/platform/settings` | ELFIS | Menu → settings ; page conservée | Indéfinie | `/team` → settings |
| `/documents` | `/platform/documents` + vue Compta | ELFIS Vault | — | Indéfinie | Filtre métier |
| `/copilote` | `/accounting/assistant` + Aura | Compta ctx / Core | — | Indéfinie | Aura |
| `/settings` | `/settings` | Compta | — | Indéfinie | Séparer OCR vs identité |
| `/organisation` | `/platform/settings` | ELFIS | Menu | Indéfinie | Layout Core |
| `/sales/*` | `/sales/*` | Sales | — | — | — |
| `/home` | `/home` | ELFIS | — | — | — |
| `/platform/settings` | `/platform/settings` | ELFIS | — | — | — |

## Redirects créés (S1.0)

| Alias | Cible |
|-------|-------|
| `/quotes` | `/devis` |
| `/catalog` | `/catalogue` |
| `/sales/catalog` | `/catalogue` |
| `/sales/quotes` | `/devis` |
| `/team` | `/platform/settings` |

## Non fait (volontaire)

- Pas de redirect cassant `/devis` → Sales  
- Pas de `/platform/documents` sans page  
- Pas de déplacement physique des pages sous autre layout
