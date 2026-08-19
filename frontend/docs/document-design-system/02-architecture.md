# 02 — Architecture DDS V1

## Composants conceptuels (nécessaires V1)

| Composant | PDF (ReportLab) | Live preview |
|-----------|-----------------|--------------|
| DocumentPage | `SimpleDocTemplate` A4 | `.dds-preview` |
| Header / Brand | `dds_header_brand` | `.dds-preview__header` / `__brand` |
| Title | `dds_title_metadata` | `.dds-preview__doc-title` |
| Metadata | dates sans statut technique | `.dds-preview__dates` |
| PartyBlock | `dds_party_block` | `.dds-preview__party` |
| ItemsTable | `dds_items_table` | `.dds-preview__table` |
| Totals | `dds_totals` (TTC dominant) | `.dds-preview__totals` / `__ttc` |
| Notes / PaymentTerms | `dds_notes_payment` | `.dds-preview__notes` |
| LegalFooter / PageNumber | canvas footer | `.dds-preview__footer` |
| Accent | filet couleur primaire | `.dds-preview__accent` |
| Signature | non requis V1 | — |

## Modules

```
document_branding.py     → DocumentBrandProfile + DocumentRenderConfig
sales_pdf.py             → assemblage DDS premium
document-design-system/  → types, preview, IdentityVisualSection
```
