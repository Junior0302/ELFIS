# 11 — Vault documents migration

## Vault unique

Propriétaire : **ELFIS Core** (`/vault/documents` API + storage).

## Surfaces

| Surface | Route | Comportement |
|---------|-------|--------------|
| Hub plateforme | `/platform/documents` | `DocumentsPage surface="platform"` — tous types |
| Vue comptable | `/documents` | `surface="accounting"` — types filtrés + CTA ELFIS |
| Legacy | `/vault` | → `/platform/documents` |

## Types comptables filtrés

`customer_invoice`, `supplier_invoice`, `credit_note`, `bank_statement`, `expense_report`

## Interdictions respectées

- Pas de DocPilot
- Pas de second stockage
- Pas de copie de fichier
- Permissions / URL signées / checksum inchangés
