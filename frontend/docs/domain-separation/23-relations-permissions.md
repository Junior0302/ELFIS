# 23 — Relations permissions

| Cible | Mapping actuel |
|-------|----------------|
| platform.relations.read | invoice.read \| documents.read \| ai.analysis |
| platform.relations.duplicates.read | idem |
| platform.relations.manage | **non exposé S1.2** (lecture seule API) |
| accounting.customers.* | invoice.read / invoice.create (existant) |
| sales.accounts.* | permissions Sales existantes |

Sales ne modifie pas les données comptables via cette API.  
Compta ne lit pas le pipeline via cette API.
