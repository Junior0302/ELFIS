# SalesPilot Commercial Proposal Engine V1 (S1.6)

**Owner:** SalesPilot (propositions) · ComptaPilot (factures) · Vault (PDF)  
**Non-goals:** signature, paiement, conversion facture auto, IA, e-mail auto, portail client, S1.7

## Audit (synthèse)

| Capacité | Existant | Décision S1.6 |
|---|---|---|
| Deal / products | `sales_crm` | Seed lignes depuis produits |
| SalesDocument float | ComptaPilot | **Ne pas dupliquer** — nouveau modèle Decimal |
| PDF ReportLab | `sales_pdf.py` | Réutiliser pattern → Vault |
| Vault | `archive_or_reuse_pdf` | Obligatoire |
| Numérotation billing | DEV-YYYY | **SP-YEAR-SEQ** dédiée |
| Customer | models_saas | Bridge lecture seule |
| Event Bus / Search | patterns CRM | Étendre |
| Alembic | absent | SQL + create_all |

## Architecture

Module `backend/app/sales_proposals/` : models, enums, amounts, numbering, readiness, versioning (service), diff, pdf, conversion, events, router, search_indexer.

## Calculs

Arrondi monétaire **par ligne** (Decimal, ROUND_HALF_UP 2 décimales), puis somme.  
`gross → discount (none|percentage|fixed) → net → tax → total`.

## Mode hybride opportunité

`calculated_amount` / `final_amount` / `amount_mode` / `amount_override_reason` sur `SalesOpportunity`.  
Une version de proposition n’est jamais mutée silencieusement.

## Workflow

draft → preparing → review_required → approved → sent → viewed → negotiating → accepted|rejected|expired → converted  
Version sent+ verrouillée ; nouvelle version obligatoire.

## Readiness

Score 0–100 déterministe (blockers / warnings / recommendations). Envoi refusé si blockers ou sans PDF.

## Conversion

`POST …/prepare-conversion` uniquement — preview doublons (exact/possible/no_match). **Aucune facture créée.**

## Frontend

- `/sales/proposals` · `/sales/proposals/new` · `/sales/proposals/:id`
- Deal « Préparer devis » → `/sales/proposals/new?opportunity_id=`

## Limites V1

- Pas d’édition riche de lignes dans l’UI (API disponible)
- `mark-viewed` manuel (pas de tracking e-mail)
- Catalogue ELFIS : `catalog_item_id` préparé seulement
- Conversion réelle → S1.6.1 / S1.7
