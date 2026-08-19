# 05 — Picker behavior

## Cause

`UniversalPicker` avait `alwaysOpen = true` + `allowEmptyQuery: true` → liste au mount.

## Correction

- Défaut `alwaysOpen = false`, `minChars: 1`, `allowEmptyQuery: false`
- Customer / Product / Relation : fermés ; ouverture focus/saisie
- DocumentPicker : `alwaysOpen` conservé (hors Composer)
- Ligne libre : bouton dédié, n’ouvre pas le picker
- Labels : « + Ajouter un client », « Nouveau produit »
- Purge banners InventoryPilot / Source debug
