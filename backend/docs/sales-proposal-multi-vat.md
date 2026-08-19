# SalesPilot — TVA multi-taux (dette S1.6.1 / PR1.1)

## Contexte

ComptaPilot `SalesDocument` porte un **seul** `vat_rate` documentaire (`billing.create_sales_document`).

## Décision PR1.1 — Option B

Si une proposition acceptée contient **plusieurs taux de TVA distincts** sur ses lignes :

1. `conversion-preview` ajoute un **blocker** explicite et `can_confirm=false`
2. `convert-to-invoice` répond **HTTP 409** `multi_vat_unsupported`
3. Aucune conversion ne reprend silencieusement le taux de la première ligne

## UX

Le panneau `ProposalConversionPanel` affiche déjà `preview.blockers` / `state.blockers`.

## Option A (future)

Support réel TVA par ligne côté ComptaPilot — hors scope PR1.1.

## Tests

`backend/tests/sales_crm/test_proposal_invoice_bridge.py::test_multi_vat_blocked_on_preview_and_convert`
