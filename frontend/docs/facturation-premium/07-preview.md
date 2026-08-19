# 07 — Prévisualisation

## F1.0

Aperçu **structuré** branché sur le draft wizard :

- Type, client, lignes, échéance
- Totaux HT / TVA / TTC (`draftAmount*`)

## PDF officiel

Réutilise les APIs existantes **après** enregistrement brouillon :

- `api.downloadSalesDocPdf`
- Flux Documents → `SalesDocPreviewModal` (e-mail, blob PDF)

Pas de nouveau moteur PDF.
