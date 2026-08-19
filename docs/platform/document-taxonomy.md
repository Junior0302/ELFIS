# Taxonomie documentaire ELFIS

Registre unique : `DocumentTypeRegistry` (`app/document_processing/classification/taxonomy.py`).

Types : supplier_invoice, customer_invoice, invoice (ambigu), quote, purchase_order, delivery_note, credit_note, receipt, expense_report, bank_statement, contract, payroll_document, identity_document, tax_document, supporting_document, unknown.

Lecture API : `GET /api/document-processing/taxonomy` (taxonomie code, pas de mutation dans RC2.5.2).

Ne pas confondre avec :

- type MIME / fichier
- `DocumentRecord.document_type` historique (string libre, défaut `file`)
- types facture ComptaPilot
