# Schémas d'extraction (RC2.5.4)

Schémas **définis en code** (`DocumentExtractionSchemaRegistry`) — pas d'exécution de schémas arbitraires depuis la base.

| schema_key | Types supportés | Revue |
|------------|-----------------|-------|
| `generic_document_v1` | unknown, supporting_document, … | optionnelle |
| `invoice_basic_v1` | invoice, supplier/customer_invoice, credit_note | obligatoire |
| `quote_basic_v1` | quote | obligatoire |
| `receipt_basic_v1` | receipt, expense_report | obligatoire |

Types de champs : string, date, decimal, integer, boolean, currency_code, percentage, enum, object, array.  
Montants persistés en **Decimal** (sérialisation string) — jamais float.

Sélection : classification confirmée > type effectif > générique. Un type `invoice` ambigu sans confirmation → schéma générique + revue (pas de forçage facture sur un montant seul).
