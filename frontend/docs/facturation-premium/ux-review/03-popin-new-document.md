# 03 — Pop-in Nouveau document

## UX

Petite dialog centrée (`Dialog` DS `size="sm"`), overlay assombri + blur existant.

- Titre : Nouveau document
- Description : Que souhaitez-vous créer ?
- Radiogroup : Facture | Devis | Avoir (icône, nom, phrase)
- Pas de modèles (aucune source réelle)
- Annuler + Créer le document (disabled sans type)

## A11y

`role=dialog`, `aria-modal`, `aria-labelledby`, focus trap DS, Escape, X/Annuler, backdrop close seulement si rien engagé (`closeOnBackdrop={!engaged}`), retour focus via `returnFocusRef`.

## Après Créer

Transition **même overlay** → ComposerDialog (STATE 2) + URL `/facturation/documents/new?type=…`.  
Documents reste monté. Voir [17](./17-modal-composer-audit.md) / [18](./18-modal-route-strategy.md).
