# SalesPilot CRM Foundation V1 (S1.1)

**Status:** Foundation (backend source of truth + empty SPA shell)  
**Non-goals:** Kanban UI, stats, IA, Invoice creation

---

## Audit — reuse vs create

| Existing | Reuse | Notes |
|----------|-------|-------|
| Organization / Member / AuthContext | Yes | Org scoping + `auth.require` |
| Contact / Customer (ComptaPilot) | Bridge later | Optional `linked_contact_id` only |
| `Company` (filiale org) | **No** | CRM uses `SalesCompany` |
| Vault | Yes | Attachments = `vault_document_id` only |
| Event Bus | Yes | `sales.*.v1` events |
| Search Engine | Yes | 6 sales resource types |
| Product Registry / Theme | Yes | SalesPilot identity |
| Permissions RBAC | Extend | `sales.read/write/manage/...` |

---

## Relations

```
Lead → Company / Person → Opportunity → quote_document_id (SalesDocument)
                                      → Invoice (ComptaPilot — later, not S1.1)
```

Default pipeline stages: Prospection → Qualification → Découverte → Proposition → Négociation → Gagné / Perdu

---

## API

Prefix: `/api/sales/*`  
Permissions: `sales.read`, `sales.write`, `sales.manage`, `sales.pipeline.manage`, `sales.export`, `sales.admin`

---

## Frontend

Shell under `/sales/*` — empty pages, Design System only.  
Launcher: **beta** in `import.meta.env.DEV`, **coming_soon** in production.
