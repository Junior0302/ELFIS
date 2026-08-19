# 09 — Plan de tests (FP01–FP30)

Tous les cas : **À tester manuellement** (sauf mention auto).

| ID | Cas | Auto |
|----|-----|------|
| FP01 | Nav ComptaPilot affiche 5 espaces Facturation | Partiel (`navModel.test`) |
| FP02 | `/facturation` = Vue d’ensemble KPI réels | |
| FP03 | `/facturation/documents` = CRUD fp05 inchangé | Partiel (premium test) |
| FP04 | `/facturation/nouveau` ouvre le wizard | |
| FP05 | `/facturation/catalogue` → `/catalogue` | |
| FP06 | `/facturation/activite` → `/activites` | |
| FP07 | `?doc=` sur `/facturation` redirige documents | |
| FP08 | `?customer_id=` redirige nouveau + préremplit | |
| FP09 | Wizard framework progress / sidebar a11y | Auto |
| FP10 | Navigation next/back étapes | Auto |
| FP11 | Choix Facture / Devis / Avoir | |
| FP12 | Recherche client instantanée | |
| FP13 | Créer client depuis wizard | |
| FP14 | Lien ELFIS Relations | |
| FP15 | Sélection SharedRelation | |
| FP16 | Catalogue local chargé | |
| FP17 | Empty favoris / plus vendus honnêtes | |
| FP18 | Créer produit local | |
| FP19 | Contrôles dérivés draft | Auto partiel |
| FP20 | Empty « Aucun contrôle » si draft OK | |
| FP21 | Prévisualisation totaux | Auto calcul |
| FP22 | Brouillon crée SalesDoc | |
| FP23 | Envoyer (sign) après brouillon | |
| FP24 | Télécharger PDF | |
| FP25 | Programmer disabled « bientôt » | |
| FP26 | Convertir disabled « bientôt » | |
| FP27 | Steps Envoi/Archive/Compta/Confirm = shells | |
| FP28 | `/devis` toujours accessible | |
| FP29 | Build TypeScript vert | Auto `npm run build` |
| FP30 | Pas de régression FacturationPage fp05 | Partiel |

## Commandes

```bash
cd frontend
npm test -- src/wizard-framework src/comptapilot/facturation/workflow src/pages/facturation src/navModel.test.ts
npm run build
```
