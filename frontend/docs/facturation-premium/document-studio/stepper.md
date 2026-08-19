# Stepper vivant

## États visuels

| Statut machine | Glyphe | Signification |
|----------------|--------|---------------|
| `blocked` / `upcoming` | ○ | Non commencée |
| `current` | ◐ | En cours |
| `completed` | ✓ | Terminée (cliquable) |

## Implémentation

- Machine inchangée (`deriveGuidedStepStatuses`)
- Présentation via CSS `.elf-cmp-focus--studio .elf-cmp-progress__dot--*`
- Attributs DOM : `data-step-status`, `data-step-id` sur chaque `<li>`
- Transition douce ~200ms (respect reduced-motion)

## Règles V1

- Completed → jump autorisé (existant)
- Futures → disabled (existant)
- Pas de sidebar verticale
