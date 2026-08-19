# 02 — Navigation Finance

Source : `navModel.ts` (`navCategories`).

## Structure livrée (routes réelles)

| Section | Entrées | Routes |
|---------|---------|--------|
| Principal | Tableau de bord | `/dashboard` |
| Facturation | Vue d’ensemble, Documents, Devis, Catalogue, Activité | `/facturation`, `/facturation/documents`, `/devis`, `/catalogue`, `/activites` |
| Finance | Vue d’ensemble, Banque, TVA, Clôture, Centre opérationnel, Rapports | `/finance`, `/banque`, `/tva`, `/cloture`, `/cockpit`, `/reports` |
| Comptabilité | Vue d’ensemble, Propositions, Journaux, Historique | `/accounting`, `/accounting/proposals`, `/accounting/engine`, `/history` |
| Documents comptables | Liste, Importer, Centre d’import | `/documents`, `/deposit`, `/migration` |
| Clients & fournisseurs | Clients, Fournisseurs (vues métier) | `/clients`, `/fournisseurs` |
| Assistance | Assistant, Signaux, Aura | `/copilote`, `/intelligence`, `/platform/aura` |
| Paramètres | Paramètres Finance | `/settings` |

## Hors menu (pas de route dédiée)

Factures / Avoirs / Paiements / Relances / Trésorerie / Validation / Écritures séparées — restent accessibles via Documents facturation, FCC ou écrans existants ; **non inventés** dans la nav.

## Retiré

Organisation, Membres, Communications, Vault plateforme (`/platform/documents`), Paramètres plateforme, Relations globales.
