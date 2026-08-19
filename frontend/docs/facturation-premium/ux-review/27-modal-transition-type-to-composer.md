# 27 — Transition petite → grande (F1.3.1.3)

## Contrat

Au clic « Créer le document » :

1. `dispatch(ENTER_COMPOSER)` — **seul** changement de stage
2. Sync URL `/documents/new?type=`
3. **Ne pas** : closeDialog, stage closed, navigate Documents, démonter root, restore focus page, retirer overlay

Même root : contenu TypeSelection → ComposerDialogContent. Overlay continu, zéro flash Documents.

CSS : `.fp-create-flow` width/height ~200 ms ; reduced-motion → none.
Dimensions grand modal : ~92–95 vw × 88–92 vh (cible 93 vw × 90 vh).
