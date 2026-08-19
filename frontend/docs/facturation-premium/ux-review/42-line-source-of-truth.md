# 42 — Line source of truth (F1.3.2.1)

## Source unique

`draft.products` (WizardSelectedProduct[]) est la **seule** source de vérité pour :

- éditeur de lignes
- aperçu live / PDF structured preview
- totaux HT / TVA / TTC (`snapshotLiveTotals`)
- validations (`deriveWizardControls` / guided gates)
- Insights (`deriveLiveDocumentInsights`)
- payload autosave / `buildPayload` (filtre labels non vides)

## `lineKey`

Champ optionnel UI-only (`WizardSelectedProduct.lineKey`) — **non sérialisé** API. Assigné à la création (catalogue, ligne libre, nouveau produit, duplicate). Clé React = `lineKey` (plus d’index-as-id).

## `removeLine`

Immutabilité : `products.filter((_, i) => i !== index)` → `patchDraft({ products })` → recalculs dérivés + live preview + debounce autosave.

## Dernière ligne

Éditeur vide « Aucune ligne » · preview « Aucune ligne » · HT/TVA/TTC 0 · contrôles / insights nettoyés.
