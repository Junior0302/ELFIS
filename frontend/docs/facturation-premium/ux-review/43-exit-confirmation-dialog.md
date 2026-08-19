# 43 — ExitConfirmationDialog (F1.3.2.1)

## Titre

`Quitter cette facture ?` / `Quitter ce devis ?` / `Quitter cet avoir ?` selon `draft.docType`.

## Microcopy

Description courte + hint brouillon. Width CSS **420–500px** (`.fp-exit-confirm-premium`).

## Actions (hiérarchie)

1. **Enregistrer brouillon et quitter** — primaire (si dirty)
2. **Continuer la création** — focus initial sûr
3. **Quitter sans enregistrer** — destructive non dominante (style léger)

## Erreurs

Loading sur save. Échec → message + **Réessayer**, dialog **reste ouvert**. Escape / Continuer ferment sans discard.
