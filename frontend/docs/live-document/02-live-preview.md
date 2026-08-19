# 02 — Live preview

## Principe

1. **Aperçu live** (sheet structuré) : mise à jour immédiate sur toute édition draft — pas de recreation page.
2. **PDF officiel** : moteur existant (`api.openSalesDocPdfBlob`) ; refresh **debounced (~700 ms)** après update autosave/manuel.
3. Toggle **Live / PDF** dans la barre d’outils — le shell `ComposerPreview` reste monté.

## Contrôles FE (sans nouveau moteur PDF)

- Zoom ± / reset (CSS `transform: scale`)
- Fit width
- Page (`#page=N` sur blob URL — best-effort navigateur)
- Plein écran (classe CSS sur le panneau)
- Téléchargement (API existante)

## Non-objectifs

- Pas de pdf.js / worker
- Pas de reload `window.location`
- Pas de recréation complète du layout Composer à chaque frappe
