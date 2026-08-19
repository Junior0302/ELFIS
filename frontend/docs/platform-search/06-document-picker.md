# 06 — Document picker

## Sources V1

| Mode | API | Types |
|------|-----|-------|
| Défaut | `billingOverview` (`/billing/sales-overview?q=&doc_type=`) | invoice / quote / credit_note |
| `useSearchEngine` | `searchElfis` | vault_document / document / accounting_entry |

Pas d’endpoint inventé pour un type non indexé. Index billing SalesDocument = futur éventuel, hors P1.0.
