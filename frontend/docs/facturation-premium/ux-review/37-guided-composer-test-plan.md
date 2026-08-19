# 37 — Guided Composer Test Plan (F1.3.2)

## Automatisés GC01–GC40

`src/pages/facturation/facturation-guided-composer.test.tsx`  
(+ `composerStepMachine.test.ts`)

## Manuel GM01–GM25 — À tester manuellement

| ID | Scénario | Statut |
|----|----------|--------|
| GM01 | Modal ouvre sur Client | À tester manuellement |
| GM02 | Continuer sans client → message | À tester manuellement |
| GM03 | Client → Produits, PDF inchangé | À tester manuellement |
| GM04 | Produits sans ligne → gate | À tester manuellement |
| GM05 | Parcours complet 6 étapes | À tester manuellement |
| GM06 | Retour conserve le draft | À tester manuellement |
| GM07 | Jump étape completed | À tester manuellement |
| GM08 | Finalization future bloquée | À tester manuellement |
| GM09 | Ratio editor/preview desktop | À tester manuellement |
| GM10 | Header progression compact | À tester manuellement |
| GM11 | Footer Retour/Continuer | À tester manuellement |
| GM12 | Review insights sans doublon | À tester manuellement |
| GM13 | Finalization Enregistrer réel | À tester manuellement |
| GM14 | Confirmation post-save dans modal | À tester manuellement |
| GM15 | Pickers fermés au mount | À tester manuellement |
| GM16 | Focus heading à chaque étape | À tester manuellement |
| GM17 | Escape / Annuler dirty | À tester manuellement |
| GM18 | Mobile stack preview | À tester manuellement |
| GM19 | Reduced-motion OK | À tester manuellement |
| GM20 | Documents inert derrière | À tester manuellement |
| GM21 | Autosave même draft | À tester manuellement |
| GM22 | Page mode freeform legacy | À tester manuellement |
| GM23 | Deep link modal guidé | À tester manuellement |
| GM24 | Empty PDF utile | À tester manuellement |
| GM25 | Fermeture → Documents immédiat | À tester manuellement |
