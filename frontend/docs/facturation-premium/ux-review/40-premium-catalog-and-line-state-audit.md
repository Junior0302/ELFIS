# 40 — Premium catalog & line state audit (F1.3.2.1)

## Bugs observés (manuel)

| # | Symptôme | Cause exacte | Fichier |
|---|----------|--------------|---------|
| 1 | « Ouvrir le catalogue » quitte le Composer / ramène Home | `ProductPicker` → `UniversalPicker` rend `<Link to={openHref} target="_blank">` ; Composer passait `openCatalogHref="/catalogue"` | `ProductPicker.tsx`, `UniversalPicker.tsx` l.81–83, `FacturationComposerPage` `LinesSection` |
| 2 | Suppression ligne → PDF / totaux / contrôles parfois stale | Clés React `key={\`line-${index}\`}` (index-as-id) → réconciliation incorrecte après `filter` ; pas de `lineKey` stable | `FacturationComposerPage.tsx` `LineEditor` |
| 3 | Dialogue annulation faible | `Dialog` générique « Modifications non enregistrées », actions plates sans hiérarchie ni microcopy type | Exit confirm inline dans `FacturationComposerPage` |

## Flux audités

- Action catalogue / `window.open` / routes `/catalogue`
- Smart Library (`useResourceLibrary`) / `ProductPicker` / `ResourceSource`
- `draft.products` (alias métier « lines ») → preview / totaux / validations / insights
- Handler `removeLine` / autosave
- Unsaved exit dialog

## Hors scope (inchangé)

Calculs métier, APIs facturation, moteur PDF, Vault, Billing, mailer, root modal / overlay workflow (`DocumentCreationModalRoot`, `ComposerDialog` stage machine).

## Corrections retenues

1. `LibraryCatalogDrawer` (Drawer overlay, priorité modal enfant) + bouton « Parcourir catalogue » — **aucune** navigation / nouvel onglet
2. `lineKey` stable + remove immuable sur `draft.products` ; preview / totaux / insights dérivés uniquement du draft
3. `ExitConfirmationDialog` premium (titre type, hiérarchie actions, loading / erreur)
