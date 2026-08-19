# 01 — Runtime audit (points interactifs)

Audit F1.3 avant / après assemblage Live Document.

## Surfaces interactives

| Zone | Comportement | Source |
|------|--------------|--------|
| Type document | Sélection → draft + preview live | `DocTypeStep` |
| Client | CustomerPicker in-composer + résumé | `ClientStep` / Smart Search |
| Produits | ProductPicker Smart Library + lignes + aperçu dernier pick | `ProductsStep` |
| Qté / prix / remise / TVA ligne | Édition → totaux + preview ciblés | `LineEditor` |
| TVA doc / notes / échéance | Inspector → totaux + preview | `ComposerInspector` |
| Totaux | HT / remises / TVA / TTC / échéance date | `LiveTotals` + `draftAmount*` |
| Insights | Confirmation client/produit, TVA inhabituelle, montant élevé, produit récent* | `deriveLiveDocumentInsights` |
| Validation | Issues → InsightList | `deriveWizardControls` |
| Autosave | Debounce 2,5 s post-create | `saveDraft({ silent })` |
| Preview live | Sheet structuré sans reload page | React state |
| Preview PDF | Blob API existante, refresh debounce post-update | `openSalesDocPdfBlob` |
| Zoom / largeur / page / plein écran | Contrôles FE sur iframe / CSS | `ComposerPreview` |
| Statut | draft / ready / validation_required / error / sent | `deriveLiveDocumentStatus` |
| Téléchargement | API existante | `downloadSalesDocPdf` |

\* Produit récent uniquement si `catalogCreatedAt` exposé par le catalogue.

## Gaps volontairement non inventés

- Document similaire (pas d’historique API Composer)
- Favoris / plus vendus
- Multi-pages PDF riches (viewer navigateur + `#page=N` best-effort)

## Interdictions respectées

Pas de nouveau moteur, pas de modification Billing / Vault / Financial Engine / calculs métier API.
