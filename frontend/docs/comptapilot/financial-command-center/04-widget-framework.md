# 04 — ELFIS Widget Framework V1

## Emplacement

`frontend/src/widget-framework/`

- `types.ts` — contrats (+ `WidgetVariant`)
- `WidgetContainer.tsx` — shell, états, helpers layout
- `widget-framework.css` — tokens via CSS vars (`--ps-*`), pas de vert imposé
- `index.ts` — exports publics

## Rôle

Fournir une **coquille produit-agnostique** : titre, toolbar refresh discret, états loading / ready / refreshing / empty / error, footer source + MAJ secondaire.

## Variants (S1.2.5.1)

`compact` | `standard` | `chart` | `list` | `hero` | `score`

## Helpers

`WidgetGrid`, `WidgetSection`, `WidgetMetric`, `WidgetList`, `WidgetChartBody`

## Refresh

Bouton icône + `aria-label` (`Actualiser {title}`) ; label texte masqué en variant compact.

## Footer

Classe `ew-footer--secondary` — source / MAJ moins dominante.

## Consommateur V1

Financial Command Center (ComptaPilot). Aucune dépendance inverse framework → FCC.

## Extension future

Autres produits (Sales, Doc…) peuvent importer le framework sans hériter des couleurs Compta.
