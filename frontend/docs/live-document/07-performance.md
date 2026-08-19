# 07 — Performance

| Technique | Usage |
|-----------|--------|
| `useMemo` | controls, liveTotals, liveInsights, liveStatus, structuredPreview, definition |
| Debounce | autosave 2,5 s ; PDF reload 700 ms |
| Génération PDF | `pdfGenerationRef` annule blobs obsolètes |
| Update ciblée | sheet live vs iframe PDF ; shell Preview stable |
| Lazy route | Composer déjà lazy dans `App.tsx` |
| CSS scale | zoom sans re-fetch |

Évité : remount complet du layout à chaque frappe ; recreation PDF à chaque keystroke.
