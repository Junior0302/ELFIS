# Document Business Validation (RC2.5.5)

Validation **métier documentaire** ELFIS — distincte de la validation de schéma (RC2.5.4) et de toute validation fiscale/comptable ComptaPilot.

## Vocabulaire

| Terme | Rôle |
|-------|------|
| BusinessValidationResult | Résultat des règles métier ELFIS |
| ValidationIssue | info / warning / error / critical |
| ProcessingPackage | Paquet immuable pour un produit |
| ProductBridge | Contrat de transmission |

Ne pas appeler cette étape « validation comptable ».

## Pipeline

`document_business_validation_v1` — désactivé par défaut (`DOCUMENT_BUSINESS_VALIDATION_ENABLED=false`).

Tolérances Decimal : `DOCUMENT_VALIDATION_AMOUNT_TOLERANCE=0.02`, `DOCUMENT_VALIDATION_PERCENTAGE_TOLERANCE=0.01`.

## Rule sets

- `invoice_document_validation_v1`
- `quote_document_validation_v1`
- `receipt_document_validation_v1`
- `generic_document_validation_v1`

Aucun plan comptable, journal, compte 401/411, ni déductibilité fiscale.
