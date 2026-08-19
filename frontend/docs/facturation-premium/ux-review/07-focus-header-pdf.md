# 07 — Focus / Header / PDF

## Focus (F1.3.1 → F1.3.1.1 Full Focus)

- Nav espaces Facturation masquée sur `/nouveau`
- **Full Focus** : sidebar Compta, Guide Banner, SubscriptionBanner masqués via `WorkspaceLayout` + `isComposerFullFocusPath`
- `ComposerFocusLayout` : plein viewport (topbar plateforme seule)
- Voir [11-full-focus-mode-audit.md](./11-full-focus-mode-audit.md), [12](./12-composer-focus-layout.md), [13](./13-focus-routing.md)

## Header

Gauche : Retour Documents, type, titre, statut. Centre : autosave, points à vérifier. Droite : max 1 primaire + 2 secondaires (Annuler / Enregistrer brouillon + Vérifier ; Continuer envoi si prêt).

## PDF

`ComposerPreview` existant (zoom, fit, fullscreen, empty/loading/error) — pas de nouveau moteur.

## Exit

Confirm si brouillon local non enregistré ; sinon retour Documents (avec `?doc=` si créé). Post-création : confirmation dans Focus (Ouvrir / Documents / Créer autre).
