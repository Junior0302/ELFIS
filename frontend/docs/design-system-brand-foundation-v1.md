# ELFIS Design System — Brand Foundation V1 (E1.1)

## Architecture

```
ELFIS Core (plateforme mère)
        ↓
     Pilot (identité visuelle)
        ↓
  Composants / layouts / UX partagés
```

Le Design System vit dans `frontend/src/design-system/`.

**E1.1 = architecture uniquement.** Aucun token n’est branché sur `:root`, aucun composant métier n’est recoloré.

## Arborescence

```
frontend/src/design-system/
  index.ts              # exports publics
  types/                # ProductId, tokens, product definition
  colors/               # palettes officielles par produit
  products/             # Product Registry (source unique)
  tokens/               # pilot-* token maps (non appliqués)
  themes/               # interfaces DesignTheme / ProductTheme
  branding/             # conventions de chemins assets

frontend/public/branding/
  README.md             # emplacement futur des logos / favicons
```

## Product Registry

Source unique : `products/registry.ts`.

Chaque produit définit :

| Champ | Rôle |
|---|---|
| `id` | Identifiant stable (`comptapilot`, …) |
| `name` / `shortName` | Libellés produit |
| `description` | Description courte |
| `status` | `active` \| `beta` \| `coming_soon` |
| `colors` | primary / secondary / accent / chartPalette |
| `branding` | chemins icon / logo / favicon |

Produits déclarés :

- **ELFIS Core** — active (plateforme)
- **ComptaPilot** — active (runtime actuel)
- SalesPilot, DocPilot, HRPilot, LegalPilot, InventoryPilot, MarketingPilot, ProjectPilot, SupportPilot — `coming_soon`

## Palette

Les couleurs sont centralisées dans `colors/palettes.ts`.

| Produit | Direction |
|---|---|
| ELFIS Core | Bleu nuit premium `#0B1F3A` |
| ComptaPilot | Vert émeraude `#0B3D2E` (aligné UI actuelle) |
| SalesPilot | Bleu professionnel |
| DocPilot | Violet |
| HRPilot | Orange |
| LegalPilot | Bordeaux |
| InventoryPilot | Cyan |
| MarketingPilot | Jaune / or UI |
| ProjectPilot | Turquoise |
| SupportPilot | Indigo |

## Tokens (non appliqués)

Noms préparés (`tokens/pilotTokens.ts`) :

- `pilot-primary`, `pilot-secondary`, `pilot-accent`
- `pilot-surface`, `pilot-surface-hover`, `pilot-border`
- `pilot-ink`, `pilot-muted`
- `pilot-success`, `pilot-warning`, `pilot-danger`, `pilot-info`
- `pilot-chart-1` … `pilot-chart-8`

Futures variables CSS : `--pilot-primary`, etc. — **pas encore injectées**.

## Conventions de nommage

- Produit : `kebab-case` id (`salespilot`)
- Tokens : préfixe `pilot-`
- CSS vars futures : préfixe `--pilot-`
- Assets : `/branding/products/<product-id>/{icon|logo|logo-mark|favicon}.svg`

Voir aussi : [Product Identity V1 (E1.1.1)](./design-system-product-identity-v1.md).

## Hiérarchie visuelle (cible)

1. **ELFIS Core** — chrome plateforme, shell multi-Pilot
2. **Pilot** — couleur / logo / accent du métier courant
3. **Composants** — boutons, badges, layouts partagés (inchangés en E1.1)

## État legacy actuel (hors Design System)

`frontend/src/index.css` `:root` utilise encore :

- `--forest`, `--mint`, `--mint-soft`, `--ink`, `--sand`, `--amber`, `--danger`

Cockpits Platform / Developer ont leurs propres scopes (`--pc-*`, `--dev-*`).

Ces variables restent la vérité visuelle runtime jusqu’à une phase d’application explicite.

## Interdictions E1.1

Ne pas modifier ni recolorer :

- Dashboard, Sidebar, Buttons
- Command Center, Decision Center, Work Queue
- Enterprise Setup, ComptaPilot screens

## Usage (lecture seule)

```ts
import { getProduct, buildPilotTokens, DEFAULT_RUNTIME_PRODUCT_ID } from './design-system'

const product = getProduct(DEFAULT_RUNTIME_PRODUCT_ID)
const tokens = buildPilotTokens(product.id)
// Ne pas appliquer `tokens` au DOM en E1.1.
```
