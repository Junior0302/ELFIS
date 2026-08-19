# 01 — Runtime audit (F1.3.4)

## Moteur PDF

| Élément | Réalité |
|---------|---------|
| Moteur unique | ReportLab (`sales_document_to_pdf`) — **pas** de second moteur |
| Preview blob / download / email / Vault | Tous appellent le même générateur backend |
| Live preview Composer | HTML React (`DocumentLivingPreview`) — structure alignée DDS, pas pixel-perfect |

## Surfaces

| Chemin | Source rendu | Branding |
|--------|--------------|----------|
| Live (Composer) | `DocumentLivingPreview` | `buildDocumentRenderConfig(org + draft.documentBranding)` |
| PDF iframe / download | `GET /billing/documents/{id}/pdf` | `render_config_for_document(doc, org)` via `branding_json` |
| Email + Vault | `DocumentDeliveryService` → `sales_document_to_pdf` | Idem PDF |

## Divergences connues (aperçu vs téléchargement / email / Vault)

| Aspect | Live HTML | PDF final |
|--------|-----------|-----------|
| Moteur | React/CSS | ReportLab |
| Pagination | Page 1 affichée | Multipage réelle + « Page N » |
| Logo SVG | Affichable en `<img>` | Uniquement si miniature raster |
| Remises ligne | Affichées si > 0 | Non dédiées dans le tableau PDF V1 |
| Pixel / typo | Approximation | Police Helvetica ReportLab |

**Aligné V1 :** showLogo, identité org réelle, labels type (Facturé à / Destinataire / Crédit pour), totaux TTC dominant, footer légal = données org only, pas de statut `draft` sur le PDF client.

## Templates facture / devis / avoir

Un seul template premium (`premium_v1`) ; métadonnées adaptées par `doc_type` (échéance / validité / crédit).

## Logo & org

- Org : `logo`, `primary_color`, `secondary_color`, `documents_show_logo`
- Document : `branding_json` → `{ showLogo, template }`
- Upload : PNG/JPG/SVG, max 2 Mo, `settings.manage`

## Légal

Footer = `DocumentBrandProfile.footer_parts()` — jamais inventé. Live preview affiche les mêmes parts quand l’org est chargée.
