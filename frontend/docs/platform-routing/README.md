# Platform routing — F1.3.2.3 Refresh route persistence

Correctif global : **F5 doit restaurer la même route + Pilot + org**, sans bounce silencieux vers ELFIS Core Home.

## Documents

| Doc | Contenu |
|-----|---------|
| [01-refresh-route-regression-audit.md](./01-refresh-route-regression-audit.md) | Audit reproduction + cause exacte |
| [02-bootstrap-states.md](./02-bootstrap-states.md) | États auth / org / permissions / subscription |
| [03-auth-org-pilot-guards.md](./03-auth-org-pilot-guards.md) | Guards et règles de redirect |
| [04-modal-composer-refresh.md](./04-modal-composer-refresh.md) | Refresh `/facturation/documents/new` |
| [05-catch-all-and-lazy.md](./05-catch-all-and-lazy.md) | Catch-all 404 + Suspense + chunk errors |
| [06-org-and-post-login-return.md](./06-org-and-post-login-return.md) | Org persistence + return-to |
| [07-bootstrap-ui-history.md](./07-bootstrap-ui-history.md) | BootstrapLoadingScreen, history, erreurs |
| [08-test-plan.md](./08-test-plan.md) | RR01–RR40 + RF01–RF20 manuel |
| [09-implementation-report.md](./09-implementation-report.md) | Rapport GO / NO GO (13 critères) |

## Code touché

- `subscriptionContext.tsx` — `loading` initial `true` si token+org
- `ProductAccessLayout.tsx` — bootstrap / erreur sub / org inaccessible / return from welcome
- `RequireAuth.tsx` — `from` = path+search+hash
- `login/LoginPage.tsx` — `sanitizeReturnPath`
- `App.tsx` — `RouteNotFound` + `RouteChunkErrorBoundary`
- `platform-routing/*` — helpers + écrans bootstrap

## Hors scope

- F1.4
- Moteurs métier (facturation, finance, accounting…)
