# 08 — Parité proportions sidebar (Home / Finance / Commercial)

## Problème

La sidebar Home (`ElfisGlobalNavigation` mode sidebar) divergait des rails Finance (`ComptaProductNav`) et Commercial (`SalesProductNav`) :

| Zone | Home (avant) | Finance / Sales |
|------|--------------|-----------------|
| Largeur hybrid non-unifié | `--ps-sidebar-w: 190px` | UI.P1 `240` / `56` |
| Item | `min-height: 42px`, pad `0.45/0.7`, gap `0.65` | `2.55rem`, pad `0.55/0.75`, gap `0.75` |
| Icône | `1.25rem` plain | `34×34` boxed |
| Label | `0.92rem` | `0.9rem` |
| Titre section | `0.65rem`, pad local | `0.68rem`, margin section |
| Toolbar / collapse | paddings locaux | toolbar `0.25 0.35 0.5`, btn `32px` |

## Source unique

Tokens sur `.ps-shell` (`platform-shell.css`), famille `--product-sidebar-*` :

- largeurs : `expanded` `240px`, `collapsed` `56px`, `current`, alias `--ps-sidebar-w`
- surface : `surface-pad-block-start/inline/block-end`
- item : `item-min-height`, `item-pad-block/inline`, `item-gap`, `item-radius`, `items-gap`
- typo : `label-size`, `section-title-size`, `section-title-margin`, `section-gap`
- chrome : `icon-size`, `icon-radius`, `collapse-size`, `toolbar-pad`, `collapsed-item-pad-inline`

## Consommateurs

| Surface | Fichier | Sélecteurs |
|---------|---------|------------|
| Tokens | `platform-shell/platform-shell.css` | `.ps-shell` |
| Home | `global-nav/elfis-global-navigation.css` | `.elfis-gnav__*` |
| Finance / Sales items | `index.css` | `.nav-categories`, `.nav-icon`, `.sidebar-collapse-btn` |
| Home shell | `home/home.css` | `.ps-sidebar--home` (plus de `190px`) |
| Unifié | `unified-platform.css` | surfaces navy + toolbar Sales |

## Hors scope

IA menu (NAV.CORE.1), accordion Finance/Sales, routes — inchangés.

## Tests

`sidebar-proportion-parity.test.ts` — SP01–SP06 (+ USS10 spatial sans `190px`).
