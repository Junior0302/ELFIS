# 29 — Erreurs & focus dans le modal (F1.3.1.3)

- Loading draft / API : **dans** le modal (`fp-composer-dialog__bridging` / messages Composer).
- Erreur + Réessayer : **dans** le modal — jamais close silencieux.
- Focus trap unique (root Overlay Manager).
- Escape : type_selection → close ; composer → requestExit (confirm si dirty) ; confirmation → close Documents.
- Fermeture protégée → restore Documents (filtres/scroll inert) sans hard refresh.
- **F1.3.2** : focus heading d’étape guidée (`#fp-guided-step-heading`) ; `aria-current=step` sur la barre.
