# 02 — Bootstrap states

États distincts (ne pas confondre) :

| Domaine | loading | ready | denied / error |
|---------|---------|-------|----------------|
| **auth** | `RequireAuth` + `BootstrapLoadingScreen` | user présent → outlet | unauthenticated → `/login?` + `state.from` |
| **organization** | attend memberships/orgId restore (localStorage `cp_org` + API) | orgId ∈ memberships | `OrgInaccessibleScreen` (choix org) |
| **subscription / permissions produit** | `loading && subscription == null` → phase `loading` | phase `entitled` \| `no_entitlement` | erreur API → `SubscriptionLoadError` |

## Règles

- Pendant **loading** → BootstrapLoadingScreen, **PAS** Home.
- Auth : `!user` pendant restore (`loading=true`) → wait, **jamais** `/home`.
- Org inaccessible → erreur explicite, pas Home silencieux.
- Pilot (thème / shell) : reconstruit via `resolveRuntimeProductFromPath(pathname)` + layouts ProductAccess — pas seulement mémoire React.
