# 06 — Org persistence & post-login return

## Org

- Persistée : `localStorage.cp_org` + token session (`cp_token`) + sync API `setActiveOrganization`.
- Pas de secrets métier dans localStorage au-delà token/org id (existant).
- Org hors memberships → `OrgInaccessibleScreen`.

## Post-login

1. Guard coupe → `/login` + `state.from` (ex. `/finance`).
2. Login succès → `sanitizeReturnPath(from)` → `/finance` (pas Home par défaut si `from` valide).

Fallback Home uniquement si pas de `from` valide.
