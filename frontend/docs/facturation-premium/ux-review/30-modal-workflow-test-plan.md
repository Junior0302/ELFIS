# 30 — Plan de tests MM + manuel MV (F1.3.1.3)

## Automatisés MM01–MM40

Fichier : `src/pages/facturation/facturation-modal-workflow.test.tsx`  
(+ machine : `workflow/composerModalMachine.test.ts`)  
Harness avec **`OverlayRouteBridge`** (preuve anti-régression route_change).

MC01–40 (`facturation-modal-composer.test.tsx`) mis à jour avec OverlayRouteBridge.

## Manuel MV01–MV20 — À tester manuellement

| ID | Scénario | Statut |
|----|----------|--------|
| MV01 | Documents → Créer → petite pop-in | À tester manuellement |
| MV02 | Type → Créer → agrandissement Composer sans flash | À tester manuellement |
| MV03 | Modal reste ouvert toute la création | À tester manuellement |
| MV04 | Documents flouté / inert derrière | À tester manuellement |
| MV05 | Scroll Documents bloqué | À tester manuellement |
| MV06 | Filtres conservés à la fermeture | À tester manuellement |
| MV07 | Desktop ~93vw × 90vh | À tester manuellement |
| MV08 | Reduced-motion : pas d’anim taille | À tester manuellement |
| MV09 | Escape type ferme ; Escape composer vide ferme | À tester manuellement |
| MV10 | Dirty → 3 actions confirm | À tester manuellement |
| MV11 | Post-création reste dans modal | À tester manuellement |
| MV12 | Fermer → Documents immédiat | À tester manuellement |
| MV13 | Back navigateur ferme → Documents | À tester manuellement |
| MV14 | Deep link `/documents/new?type=facture` | À tester manuellement |
| MV15 | `/documents/new` sans type → pop-in type | À tester manuellement |
| MV16 | Composer vide utilisable (client/lignes optionnels) | À tester manuellement |
| MV17 | Erreur API reste dans modal | À tester manuellement |
| MV18 | Legacy `/nouveau` → modal | À tester manuellement |
| MV19 | Focus retour sur « Créer un document » | À tester manuellement |
| MV20 | Pas de retour auto Documents pendant édition | À tester manuellement |
