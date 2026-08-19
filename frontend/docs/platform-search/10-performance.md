# 10 — Performance

| Mécanisme | Valeur |
|-----------|--------|
| Debounce | 280 ms |
| Min chars (global) | 2 |
| Abort | AbortController par requête |
| Race | reqId ignore stale |
| Cache | TTL 8 s, clé q+scope+types+org |
| Pagination | page_size limité (12–40 selon surface) |
| N+1 | évité — listes batch API existantes |

Pas de polling. Pas de préchargement massif hors pickers `allowEmptyQuery` (1 page).
