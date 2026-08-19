# 09 — Sécurité / tenant / permissions

1. Toute requête passe `token` + `orgId` via `useAuth` (jamais inventés).
2. Search Engine filtre déjà `organization_id` + feature `SEARCH_GLOBAL`.
3. Shared Relations / billing : mêmes gardes backend.
4. `action_url` / `route` : URLs internes Engine uniquement (pas d’open redirect inventé).
5. Metadata filtrée côté Engine (`search_security`) — le FE ne réintroduit pas de champs secrets.
6. Permissions Smart Search = projection `SearchPermission[]` optionnelle ; absence = pas de fake grant.
