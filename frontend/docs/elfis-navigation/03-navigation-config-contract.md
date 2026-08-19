# 03 — Contrat `elfisNavigationConfig`

## Fichier

`frontend/src/platform-shell/global-nav/elfisNavigationConfig.ts`

## Types

### Section

| Champ | Type | Rôle |
|-------|------|------|
| `id` | string | Identifiant stable |
| `label` | string \| null | Titre section (null = footer sans titre) |
| `order` | number | Ordre d’affichage |
| `placement` | `'main' \| 'footer'` | Zone |
| `permission` | string? | Gate section |
| `badge` | string? | Badge section |
| `items` | Item[] | Entrées |

### Item

| Champ | Type | Rôle |
|-------|------|------|
| `id` | string | Identifiant |
| `label` | string | Libellé UI |
| `icon` | string | Id ElfisIconSystem |
| `to` | string? | Route ou `path#hash` |
| `action` | `'logout'?` | Action non-route |
| `permission` | string? | Permission org existante |
| `badge` | string? | Badge item |
| `destructive` | boolean? | Style danger (logout) |
| `disabled` | boolean? | Non cliquable |
| `match` | `'exact' \| 'prefix' \| 'hash'` | Actif |

## Consommateurs

- `ElfisGlobalNavigation` mode `sidebar` → Home + Platform workspace
- `ElfisGlobalNavigation` mode `drawer` → hamburger global
- Helpers legacy : `globalNavModel.ts`, `platformNavModel.ts` (dérivés)

## Helpers

- `filterElfisNavSections(can)`
- `isElfisNavItemActive(pathname, hash, item)`
- `ELFIS_NAV_BACKLOG`
- `ELFIS_NAV_BRAND` (`ELFIS` / `Plateforme` / tagline)

