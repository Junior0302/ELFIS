# 02 — Contrat Smart Search

## Types

```ts
SearchQuery    { q, scope?, types?, filters?, page?, pageSize?, organizationId? }
SearchResult   { type, id, title, subtitle?, description?, icon?, metadata?, status?, route?, source, permissions?, actions?, score? }
SearchGroup    { id, label, type?, items }
SearchFilter   { key, value }
SearchScope    global | relations | customers | suppliers | documents | products | accounting
SearchAction   { id, label, kind, href?, disabled? }
SearchPermission { key, granted }
```

## SearchEntityType V1 (sources réelles uniquement)

| Type | Source |
|------|--------|
| relation / customer / supplier | SharedRelations (+ billing customers fallback) |
| document / invoice / quote / credit_note | billingOverview SalesDoc **ou** Engine (vault) |
| product / service | catalogue local (`listCatalog`) |
| accounting_entry / vault_document | Search Engine V1 |
| organization / user | **non branchés** tant qu’endpoint dédié absent |

Extensible : ajouter un type seulement avec source réelle.

## Règle moteur

- Fuzzy / ranking = **Search Engine V1** (`api.searchElfis`)
- Domaine pickers = APIs métier normalisées en `SearchResult`
- **Jamais** un second FTS / fuzzy FE
