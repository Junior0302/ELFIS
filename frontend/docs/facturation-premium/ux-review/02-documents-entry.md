# 02 — Documents = entrée

## Décision

La page Documents est le seul point d’entrée création visible.

## Implémentation

- Bouton primaire unique **Créer un document** (header droite) → ouvre `NewDocumentDialog`.
- Plus de `Link` vers `/facturation/nouveau` ni « Liste des devis » (filtre onglets Devis conservé).
- Formulaire inline de création masqué si `!editingId` (édition existante conservée).
- `?create=1` ouvre le pop-in (redirect Composer sans type).

## Fichiers

- `src/pages/FacturationPage.tsx`
- `src/pages/facturation/FacturationDocumentsPage.tsx` (wrapper inchangé)
- `src/comptapilot/facturation/NewDocumentDialog.tsx`
