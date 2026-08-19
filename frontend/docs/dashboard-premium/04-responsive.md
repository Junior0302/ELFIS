# 04 — Responsive

| Breakpoint | Comportement |
|---|---|
| > 1280 | KPI 8 colonnes ; charts héros + 2 cols ; bas 30/42/28 |
| ≤ 1280 / 1200 | KPI 4 colonnes |
| ≤ 960 | Bas 1 colonne ; half-charts restent 2 cols si largeur ok |
| ≤ 720 | KPI 2→1 (flex column) ; charts 1 col ; order mobile métier-first |

## Accessibilité

- Sections `aria-labelledby`
- Widgets titrés (`ew-title-{id}`)
- Focus-visible accent vert
- `prefers-reduced-motion` : pas d’animations / transforms
