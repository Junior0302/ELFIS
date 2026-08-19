# 25 — S1.2 test plan

## Automatisé

| Test | Résultat | Preuve |
|------|----------|--------|
| Adapter customer | OK | `test_shared_relations_s12.py` |
| Adapter supplier contact | OK | idem |
| Doublon email | OK | idem |
| Isolation org | OK | idem |
| Opaque IDs frontend | OK | `sharedRelations.s12.test.ts` |
| TypeScript / build | voir rapport | |

## Manuel Chris — TABLEAU S1.2

| ID | Parcours | Attendu | Observé | Note | Statut |
|----|----------|---------|---------|------|--------|
| R01 | Ouvrir Relations ELFIS | Liste réelle | — | — | À tester manuellement |
| R02 | Rechercher Dupont | Résultats | — | — | À tester manuellement |
| R03 | Filtrer Clients | Rôle customer | — | — | À tester manuellement |
| R04 | Filtrer Fournisseurs | Rôle supplier | — | — | À tester manuellement |
| R05 | Ouvrir une relation | Fiche détail | — | — | À tester manuellement |
| R06 | Vérifier rôles | Chips | — | — | À tester manuellement |
| R07 | Ouvrir ComptaPilot | /clients ou /fournisseurs | — | — | À tester manuellement |
| R08 | Revenir ELFIS | /platform/relations | — | — | À tester manuellement |
| R09 | Ouvrir SalesPilot | /sales/companies | — | — | À tester manuellement |
| R10 | Données commerciales | Sales inchangé | — | — | À tester manuellement |
| R11 | Créer client Compta | Persist | — | — | À tester manuellement |
| R12 | Apparition ELFIS | customer:* | — | — | À tester manuellement |
| R13 | Créer fournisseur | Persist | — | — | À tester manuellement |
| R14 | Apparition ELFIS | contact:* | — | — | À tester manuellement |
| R15 | Doublon email | Signal | — | — | À tester manuellement |
| R16 | Alerte doublon | Liste | — | — | À tester manuellement |
| R17 | Pas de fusion auto | auto_merge false | — | — | À tester manuellement |
| R18 | Permissions | 403 sans droit | — | — | À tester manuellement |
| R19 | Mobile | OK | — | — | À tester manuellement |
| R20 | Recherche / Command Center | Liens relations | — | — | À tester manuellement |
