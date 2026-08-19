# 02 — Système couleur ELFIS

## Tokens officiels

| Token | Hex | Usage |
|-------|-----|--------|
| `--elfis-navy-950` | `#071629` | Primaire structurel, boutons, sidebar |
| `--elfis-navy-900` | `#102746` | Hover / navy clair actif |
| `--elfis-navy-signature` | `#0B1F3A` | Compat launcher / gnav historique |
| `--elfis-blue-600` | `#2764E7` | Accent signature, focus, marqueur actif |
| `--elfis-blue-100` | `#EAF1FF` | Surfaces douces, badges |
| `--elfis-page` | `#F5F7FA` | Fond page |
| `--elfis-surface` | `#FFFFFF` | Cartes / panels |
| `--elfis-surface-muted` | `#F8FAFC` | Zones secondaires |
| `--elfis-border` | `#DDE4EE` | Bordures |
| `--elfis-text-primary` | `#101828` | Texte |
| `--elfis-text-secondary` | `#58657A` | Secondaire |
| `--elfis-text-muted` | `#8893A5` | Muted |
| `--elfis-success` | `#16845B` | Succès sémantique |
| `--elfis-warning` | `#C97816` | Warning |
| `--elfis-danger` | `#C83F49` | Danger |
| `--elfis-info` | `#2764E7` | Info (= blue-600) |

## Mapping Theme Engine

Produit `elfis-core` (`PRODUCT_PALETTES` + `buildPilotTokens`) :

- primary → navy-950
- secondary / accentSoft → blue-100
- accent / focus / info → blue-600
- surface → blanc ; border → `--elfis-border`
- success / warning / danger → tokens sémantiques ci-dessus

Fichiers : `elfisBrandTokens.ts`, `elfis-brand.css`, `palettes.ts`, `pilotTokens.ts`.
