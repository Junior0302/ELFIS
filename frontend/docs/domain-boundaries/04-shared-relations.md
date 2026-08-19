# 04 — Relations partagées

## Source de vérité

ELFIS Relations (`/platform/relations`) + contrat SharedRelation.

## Vues métier Finance

- `/clients` — clients facturés
- `/fournisseurs` — fournisseurs comptables

Mention UI : **« Données issues d’ELFIS Relations »**.

Lien contextuel : « Ouvrir la fiche dans ELFIS Relations » (même onglet).

## Commercial

Entreprises / Contacts SalesPilot s’appuient sur l’identité partagée.
Accès contextuel menu : **Clients → Relations** (`/platform/relations`, badge ELFIS) — pas un second CRM.

## Création

Pickers partagés (`RelationPicker`, `CustomerPicker`, Composer) — pas de nouvel onglet / second CRM.
