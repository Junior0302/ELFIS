# Design System Studio

## Tokens

| Token | Rôle |
|-------|------|
| `--ds-studio-green` | Accent premium / progression |
| `--ds-studio-warm-gray` | Fond atelier |
| `--ds-studio-white` | Cartes / PDF |
| `--ds-studio-input` | Inputs gris clair |
| `--ds-studio-blue` | Guidance discrète (conseil) |
| `--ds-studio-radius` | Coins généreux (~1.05rem) |
| `--ds-studio-shadow` | Ombres légères |
| `--ds-studio-motion` | 200ms ease |

## Surfaces

- **Fond** : gris chaud très léger
- **Cartes / panels** : blanc, padding confortable, ombre douce
- **Inputs** : fond gris clair, focus bleu discret
- **Hero** : icône + titre + phrase d’aide

## Typographie

| Niveau | Usage |
|--------|-------|
| Titre hero | ~1.35rem, weight 650 |
| Aide | 0.95rem, muted |
| Libellés | uppercase micro / field labels |
| Valeurs | weight 600 |
| Secondaire | meta, placeholders PDF |

## Motion

- Fade / rise 150–250ms
- `prefers-reduced-motion: reduce` → animations désactivées

## Fichier

`src/comptapilot/facturation/document-studio/document-studio.css`
