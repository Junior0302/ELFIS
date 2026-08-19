# ELFIS Design System — Semantic Theme Migration V1 (E1.3)

## Objectif

Migrer progressivement l’identité produit vers `--pilot-*`, sans toucher aux états métier, avec **parité visuelle ComptaPilot**.

## 1. Audit (synthèse)

| Source | Occurrences | Classe |
|---|---|---|
| `--forest` / `--forest-deep` | Boutons, nav, titres brand, nombreux écrans | 1 identité + 4 dette |
| `--mint` / `--mint-soft` | Accent, focus, surfaces soft, badges | 1 identité / 3 neutre / 2 métier (`badge.ok`) |
| `--ink` | Texte corps global | 3 surface neutre (non migré V1) |
| `#0b3d2e` / `#e7f2ec` hardcodés | Auth, Settings, gradients marketing | 1 identité / 4 dette |
| `#22c55e` / charts | FinancialDashboard | 2 état métier — **interdit** |
| `--amber` / `--danger` | Warnings, erreurs, toasts | 2 état métier — **interdit** |
| Platform `--pc-*` / Dev `--dev-*` | Cockpits | Hors scope Pilot |

## 2. Tableau des couleurs (mapping V1)

| Legacy | Token sémantique | Usage migré |
|---|---|---|
| `--forest` | `--pilot-primary` | Boutons, liens d’action, nav, sélection |
| `--forest-deep` | `--pilot-primary-hover` / `--pilot-primary-active` | Hover bouton, sidebar |
| `--mint` | `--pilot-accent` / `--pilot-focus` | Accents nav, focus rings |
| `--mint-soft` | `--pilot-secondary` / `--pilot-surface` | Hover secondary, badge accent |
| `--ink` | `--pilot-text` (préparé, peu consommé V1) | Corps texte — reporté |
| `--amber` / `--danger` | *inchangés* | États métier |

Pattern rétrocompatible :

```css
background: var(--pilot-primary, var(--forest));
```

## 3. Composants / sélecteurs migrés

- `.btn`, `.btn:hover`, `.btn:focus-visible`, `.btn.secondary`
- Sidebar + états `.nav a.active` / hover icônes / `.nav-category-btn.active` / `.nav-sublink.is-active`
- `.linkish` + focus
- Focus champs `.field` / auth
- `.badge` (accent produit uniquement)
- `.ui-card-link`, `.ui-list a`
- Work Queue onglets `.work-queue-counts button.is-active`
- Enterprise Setup sélection / focus
- `fi-cta-primary:focus-visible`, `.fi-cta-secondary`
- Auth aside + liens d’action (`auth.css`)
- `DocumentsPage` status color
- Settings brand swatches
- Brand preview headings / border

## 4. Volontairement non migrés

- `.btn.danger-outline`, `.badge.ok/.warn/.danger`, `.ui-badge--ok/--warn/--danger`
- `.ui-toast--success/--error`, `auth-alert-ok/error`, password-reset success
- Confidence meter mid/low, pipeline « done », first-action-success
- Graphiques / FinancialDashboard (`#22c55e`, donuts)
- Surfaces neutres (`--sand`, body gradients, `--ink` global)
- Platform Cockpit / Developer Cockpit
- HomeParticles RGB canvas

## 5. Comparaison avant/après (ComptaPilot)

Tokens ComptaPilot alignés exactement :

- primary `#0B3D2E` = `--forest`
- primaryHover/Active `#07281E` = `--forest-deep`
- secondary/surface `#E7F2EC` = `--mint-soft`
- accent/focus `#7BC4A0` = `--mint`

→ Rendu métier **inchangé** pour ComptaPilot.

## 6. Sandbox

Sur `/dev/design-system/themes`, changer de produit met à jour les `--pilot-*` du host sandbox. Les exemples neutres (déjà E1.2) + boutons métier globaux (sur `documentElement`) restent ComptaPilot en mode application.

## 7–8. Tests / Build

Voir suite `design-system*.test.ts` + build frontend.

## 9. Dettes

- Migrer titres / cards restants encore en `--forest`
- Remplacer HEX marketing restants
- Contraste automatisé (E1.6)
- Consommer `--pilot-chart-*` dans les graphiques (E1.4+)
- Ne pas commencer E1.4 ici
