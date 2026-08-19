# 04 — Universal Picker framework

`UniversalPicker` compose `SmartSearch` + actions create/open + slot sélection.

| Picker | Scope | Source |
|--------|-------|--------|
| RelationPicker | relations / customers / suppliers | SharedRelations |
| CustomerPicker | customers | SharedRelations + billing fallback + createCustomer |
| SupplierPicker | suppliers | SharedRelations role=supplier |
| DocumentPicker | documents (ou global Engine) | billingOverview / Engine |
| ProductPicker | products | ProductSource (local catalog) |

Create action = callback configurable branché sur workflows existants uniquement.
