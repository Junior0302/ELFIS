# 05 — Document status

## États (`ComposerDocStatus`)

| Status | Label | Couleur / icône | Quand |
|--------|-------|-----------------|-------|
| `draft` | Brouillon | accent | Édition / non enregistré simple |
| `ready` | Prêt | vert | Brouillon OK, contrôles non bloquants |
| `validation_required` | Validation requise | ambre | Warnings/errors ou incomplet |
| `error` | Erreur | rouge | Autosave error |
| `sent` | Envoyé | navy | Après action `sign` existante |
| `unknown` | — | — | Réserve type |

`statusHint` explique la cause (issue réelle ou message autosave). Affiché via `ComposerStatus` (`aria-live`).
