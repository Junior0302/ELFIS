# 56 — Test plan LDI01–LDI40 + manuel SI (line deletion)

## Automatisés

`src/pages/facturation/facturation-line-deletion.test.tsx` — LDI01–LDI40

## Manuel SI01–SI20 — À tester manuellement

| ID | Scénario | Statut |
|----|----------|--------|
| SI01 | Catalogue → ajouter → supprimer → disparition immédiate | À tester manuellement |
| SI02 | Pas de fantôme sous le picker | À tester manuellement |
| SI03 | Preview live HT/TTC à 0 si dernière ligne | À tester manuellement |
| SI04 | Deux lignes, supprimer 1ère | À tester manuellement |
| SI05 | Continuer/Retour sans changement d’état | À tester manuellement |
| SI06 | Autosave pendant delete | À tester manuellement |
| SI07 | Fade-out ~150ms | À tester manuellement |
| SI08 | reduced-motion : delete immédiat | À tester manuellement |
| SI09 | Insights / contrôles sync | À tester manuellement |
| SI10 | Ligne libre delete | À tester manuellement |
| SI11 | Multi-ajout catalogue puis delete | À tester manuellement |
| SI12 | Duplicate puis delete copie | À tester manuellement |
| SI13 | PDF mode live sync | À tester manuellement |
| SI14 | Pas de navigation requise | À tester manuellement |
| SI15 | Toast Ajouté disparaît, pas selected sticky | À tester manuellement |
| SI16 | Empty state « Aucune ligne » | À tester manuellement |
| SI17 | Dirty flag après delete | À tester manuellement |
| SI18 | Remount step items cohérent | À tester manuellement |
| SI19 | Mobile delete | À tester manuellement |
| SI20 | Escape catalogue ouvert + delete ligne derrière | À tester manuellement |
