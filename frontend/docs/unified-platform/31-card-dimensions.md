# 31 — Card dimensions

| Card | Règle |
|------|-------|
| MetricCard (`.up-metric-card`) | `min-height: 132px`, surface neutre |
| ChartCard body | `clamp(300px, 28vh, 420px)` |
| ChartCard hero | `clamp(340px, 32vh, 480px)` |
| ChartCard weak | min ~7.5rem, max ~11rem — pas de vide énorme |
| Surfaces | neutres ; vert/bleu = accent Pilot only |

`ResponsiveChartFrame` : ResizeObserver → largeur SVG.
