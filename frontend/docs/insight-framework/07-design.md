# 07 — Design

## Tokens

Couleurs via variables Design System :

- `--pilot-success`
- `--pilot-warning`
- `--pilot-danger`
- `--pilot-info`

Accent local composant : `--elf-insight-accent` (dérivé du type).

## Motion

- Entrée discrète toast / stack (`elf-insight-enter`)
- Transitions courtes hover / focus
- **`prefers-reduced-motion: reduce`** → animations / transitions désactivées

## Relation Widget Framework

| Couche | Rôle |
|--------|------|
| Widget | Container (titre, statut loading/empty/error, grille) |
| Insight | Contenu signal à l’intérieur (ou hors widget) |

Ne pas recréer des containers Insight qui dupliquent `WidgetContainer`.
