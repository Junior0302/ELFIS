# 02 — Platform tokens

Consolidation **sans forker** le Theme Engine / foundation.

## Sources de vérité

| Famille | Source | CSS |
|---------|--------|-----|
| Spacing | `SPACE_SCALE` / `foundationTokens` | `--space-1` … `--space-12` |
| Radius | `RADIUS_SCALE` | `--radius-sm` … `--radius-pill` |
| Shadows | `SHADOW_SCALE` | `--shadow-sm/md/lg` |
| Container | `CONTAINER_SCALE` | `--container-sm` … `--xl` |
| Pilot accents | `buildPilotTokens` + RuntimeThemeSync | `--pilot-*` |
| Chrome navy | platform-shell | `--platform-shell-bg` etc. |

## Module

`unified-platform/platformTokens.ts` — `PLATFORM_SPACE`, `PLATFORM_RADIUS`, `PLATFORM_SHADOW`, `PLATFORM_SURFACES`, `PLATFORM_BORDERS`, `PLATFORM_TYPOGRAPHY`, `PLATFORM_SHELL_DIMENSIONS`.

Sous `.up-shell.up-shell--unified` : variables `--up-*` (surfaces, borders, typo, shell dims) qui **réutilisent** les valeurs existantes.

## Dimensions shell (identiques 3 Pilots)

| Token | Valeur |
|-------|--------|
| Topbar | 64px |
| Sidebar expanded | 240px |
| Sidebar collapsed | 56px |
| Transition | 180ms |

**Interdit :** dimensions différentes par Pilot.
