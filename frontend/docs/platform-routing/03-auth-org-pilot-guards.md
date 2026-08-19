# 03 — Auth / org / pilot guards

## RequireAuth

- `loading` → BootstrapLoadingScreen
- `!user` → `/login` avec `state.from = pathname + search + hash`
- sinon → `<Outlet />`

## ProductAccessLayout

1. phase `loading` → BootstrapLoadingScreen
2. `error && !subscription` (non admin) → SubscriptionLoadError
3. orgId hors memberships → OrgInaccessibleScreen
4. `no_entitlement` + path non public → `/welcome` + `state.from`
5. entitled + `/welcome` → `sanitizeReturnPath(from)` (sinon `/home`)
6. sinon layouts : Enterprise / Home / Platform / Sales / Workspace

## Pilot

`RuntimeThemeSync` + `resolveRuntimeProductFromPath` dérivent le produit de l’URL au refresh (ComptaPilot, SalesPilot, ELFIS Core).
