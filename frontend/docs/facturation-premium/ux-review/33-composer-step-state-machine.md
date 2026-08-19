# 33 — ComposerStep state machine (F1.3.2)

## Séparation

| Machine | Rôle |
|---------|------|
| `ComposerModalStage` | Overlay : closed / type_selection / composer / confirmation |
| `ComposerStep` | Contenu guidé **dans** stage `composer` |

Fichier : `workflow/composerStepMachine.ts`

## Étapes

`client` → `items` → `terms` → `notes_payment` → `review` → `finalization`

## Règles

- Étapes **completed** cliquables (barre progression)
- Étapes **futures** = `blocked` (V1)
- Validation `validateComposerStep` avant Continuer
- Même draft / autosave tout au long
