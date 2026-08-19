# 04 — Preview

## États

| État | Contenu |
|------|---------|
| `empty` | Aperçu structuré draft + message PDF après brouillon |
| `loading` | Chargement blob PDF |
| `ready` | iframe PDF (`api.openSalesDocPdfBlob`) |
| `error` | Message + Réessayer |

## Moteur

Réutilise APIs existantes uniquement — **pas de nouveau moteur PDF**.

- Download : `api.downloadSalesDocPdf`
- Blob : `api.openSalesDocPdfBlob`
- Envoi riche / zoom avancé multi-pages : via Documents → `SalesDocPreviewModal` (existant)

Zoom label « 100 % » affiché quand ready (pas de moteur zoom inventé).
