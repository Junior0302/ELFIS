# 05 — Contrats de données partagées

Sans duplication de tables. Interfaces conceptuelles pour les vues produit.

## ELFIS Relations Contract

| Champ | Description |
|-------|-------------|
| partyId | Identifiant référence |
| organizationId | Tenant |
| displayName | Nom affiché |
| legalName | Raison sociale |
| emails / phones / addresses | Coordonnées |
| roles[] | customer, supplier, prospect, employee, partner |
| status | active / archived |

## Sales Customer View

| Champ | Description |
|-------|-------------|
| partyId | Ref ELFIS |
| pipelineContext | Étape commerciale |
| opportunities | Liens opportunités |
| commercialOwner | Owner Sales |
| activities | Activités CRM |

## Compta Customer View

| Champ | Description |
|-------|-------------|
| partyId | Ref ELFIS |
| billingIdentity | Infos facturation |
| taxIdentity | TVA / SIRET usage facture |
| paymentTerms | Conditions |
| invoices / balance | Soldes Compta |

## Vault Document Reference

| Champ | Description |
|-------|-------------|
| documentId | Id Vault |
| ownerApplication | comptapilot / salespilot / elfis-core |
| entityType / entityId | Lien métier |
| documentCategory | invoice, quote, import… |
| storageReference | Path bucket |
| checksum | Intégrité |

## S1.0

- Contrats **documentés uniquement**  
- Pages existantes non refactorées vers ces types  
- Migration tables = **S1.2+** avec plan validé
