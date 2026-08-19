# Architecture — Commercial Proposal Engine V1

## Propriété

- SalesPilot : propositions, versions, lignes, readiness, workflow
- ComptaPilot : factures / clients (bridge lecture)
- Vault : PDF immuables

## Arrondis

1. Quantité : 3 décimales  
2. Montants ligne : 2 décimales après chaque étape (gross, discount, tax, total)  
3. Totaux proposition : somme des montants déjà arrondis

## Catalogue futur

`catalog_item_id` facultatif — pas de catalogue SalesPilot isolé. Service partagé prévu : **ELFIS Product Catalog**.
