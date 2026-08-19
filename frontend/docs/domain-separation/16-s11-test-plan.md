# 16 — S1.1 test plan

## TABLEAU A — Tests Cursor

| Test | Résultat | Preuve | Fichier | Commentaire |
|------|----------|--------|---------|-------------|
| Nav modèle Core | OK | vitest | `platform-workspace.s11.test.tsx` | 8 items |
| Layout elfis-core | OK | vitest | idem | pas sidebar Compta/Sales |
| Redirects legacy | OK | vitest | `domainSeparation.s1.test.tsx` | team, org, vault, equipe |
| Nav Compta liens Core | OK | vitest | `navModel.test.ts` | members/org |
| Home sidebar | OK | vitest | `HomePlatformSidebar.test.tsx` | raccourcis |
| Launcher footer | OK | vitest | `launcherModel.test.ts` | org/docs/relations/comms |
| Identity / thème | OK | vitest | `navigation-product-identity.test.tsx` | |
| TypeScript / build | OK | `tsc -b && vite build` | — | 2026-08-01 |

## TABLEAU B — Test manuel Chris

| ID | Parcours | Attendu | Observé | Note | Statut | Capture | Commentaire |
|----|----------|---------|---------|------|--------|---------|-------------|
| M01 | Home → Organisation | `/platform/organization` | — | — | À tester manuellement | — | |
| M02 | Modifier org | Persistée API | — | — | À tester manuellement | — | |
| M03 | Donnée sur facture | Identité PDF OK | — | — | À tester manuellement | — | |
| M04 | Home → Membres | `/platform/members` | — | — | À tester manuellement | — | |
| M05 | Vérifier équipe | Liste réelle | — | — | À tester manuellement | — | |
| M06 | Compta → Équipe → Core | members | — | — | À tester manuellement | — | |
| M07 | Home → Documents | Vault hub | — | — | À tester manuellement | — | |
| M08 | Ouvrir PDF Vault | URL signée | — | — | À tester manuellement | — | |
| M09 | Documents comptables | Filtre + CTA | — | — | À tester manuellement | — | |
| M10 | Ouvrir tous docs ELFIS | `/platform/documents` | — | — | À tester manuellement | — | |
| M11 | Communications | Status sans secret | — | — | À tester manuellement | — | |
| M12 | Provider sans secret | Pas de clé | — | — | À tester manuellement | — | |
| M13 | Compta config e-mail | Lien Core | — | — | À tester manuellement | — | |
| M14 | Route ELFIS | communications | — | — | À tester manuellement | — | |
| M15 | Home → Aura | `/platform/aura` | — | — | À tester manuellement | — | |
| M16 | Assistant financier | `/copilote` + lien Aura | — | — | À tester manuellement | — | |
| M17 | Relations | Projection | — | — | À tester manuellement | — | |
| M18 | Client partagé | Rôles affichés | — | — | À tester manuellement | — | |
| M19 | Retour Compta | Sidebar verte | — | — | À tester manuellement | — | |
| M20 | Thèmes / nav | Stable | — | — | À tester manuellement | — | |
