# 01 — Workflow Facturation Premium (F1.0)

## Objectif

Fondations du **workflow officiel** de création / gestion des documents commerciaux (facture, devis, avoir) via un parcours guidé (wizard), sans remplacer le CRUD `/facturation/documents`.

## Étapes officielles

| # | Id | Libellé | Statut F1.0 |
|---|----|---------|-------------|
| 1 | `document-choice` | Choix du document | Branché (UI) |
| 2 | `client` | Client | Branché (customers + SharedRelation) |
| 3 | `products` | Produits | Branché catalogue **local** |
| 4 | `controls` | Contrôles | Dérivés du draft wizard uniquement |
| 5 | `preview` | Prévisualisation | Aperçu draft ; PDF via API après brouillon |
| 6 | `validation` | Validation | Brouillon / Envoyer / Télécharger branchés ; Programmer / Convertir = bientôt |
| 7 | `send` | Envoi | Shell + lien flux existant |
| 8 | `archive` | Archivage | Shell honnête |
| 9 | `accounting` | Comptabilisation | Shell + lien Accounting |
| 10 | `confirmation` | Confirmation | Shell |

## Code

- Types / machine : `frontend/src/comptapilot/facturation/workflow/`
- UI : `frontend/src/pages/facturation/FacturationWizardPage.tsx`
- Route : `/facturation/nouveau`

## Règles

- Aucun moteur métier modifié
- Aucune donnée inventée dans les contrôles
- InventoryPilot : non branché (`catalogSource: 'local'` par défaut)
