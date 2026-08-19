# 05 — Contrat widget

## `WidgetDefinition`

| Champ | Description |
|---|---|
| `id` | Identifiant stable (`data-widget-id`) |
| `title` | Titre accessible (`aria-labelledby`) |
| `category` | `observe` \| `alert` \| `forecast` \| `action` \| `explain` |
| `status` | `idle` \| `loading` \| `ready` \| `refreshing` \| `empty` \| `error` |
| `refreshable` | Affiche le bouton Actualiser |
| `source` | Provenance affichée (ex. Financial Engine) |
| `lastUpdatedAt` | Horodatage MAJ |
| `emptyTitle` / `emptyDescription` | Empty state |
| `errorMessage` | Message erreur |

## États de rendu

| Status | Corps |
|---|---|
| `loading` | Skeleton |
| `error` | Message + retry |
| `empty` | Empty state |
| `ready` / `refreshing` / `idle` | `children` |

## Accessibilité minimale

- `section` + `aria-labelledby`
- `aria-busy` / `aria-label` sur skeleton
- `role="alert"` erreur, `role="status"` empty
- bouton refresh `aria-label="Actualiser {title}"`
